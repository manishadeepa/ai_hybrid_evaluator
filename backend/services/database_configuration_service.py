"""Validate connection profiles and safely activate app JSON storage folders."""

import json
import os
import hashlib
import shutil
import platform
import socket
import ssl
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.repositories.json_repository import JSONRepository
from backend.data_paths import (
    DEFAULT_DATA_DIR,
    STABLE_DATA_DIRECTORIES,
    STABLE_DATA_FILES,
    copy_file_no_overwrite,
    data_files_equal,
    get_active_data_dir,
    save_active_data_dir,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DatabaseConfigurationService:
    """Test server-side storage connectivity and persist encrypted profiles."""

    PROFILE_TYPES = {"folder", "mysql", "api"}
    AUTH_TYPES = {"API Key", "Bearer Token", "Basic Auth", "None"}
    SSL_MODES = {"DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"}
    MAX_CERTIFICATE_BYTES = 1024 * 1024

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
        self.config_path = self.data_dir / "database_configurations.json"
        self.certificate_dir = self.data_dir / "db_ca_certs"

    def _records(self):
        if not self.config_path.exists():
            return []
        rows = JSONRepository(self.config_path).get_all()
        profile_types = [row.get("profile_type") for row in rows]
        if (
            any(profile_type not in self.PROFILE_TYPES for profile_type in profile_types)
            or len(profile_types) != len(set(profile_types))
        ):
            raise ValueError("Invalid database configuration profiles.")
        return rows

    def _cipher(self):
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        key = os.getenv("AI_CONNECTION_ENCRYPTION_KEY", "")
        if not key:
            raise ValueError(
                "AI_CONNECTION_ENCRYPTION_KEY is required to save credentials securely."
            )
        try:
            return Fernet(key.encode("utf-8"))
        except ValueError as exc:
            raise ValueError("AI_CONNECTION_ENCRYPTION_KEY is invalid.") from exc

    def _credentials(self, profile_type):
        row = next(
            (item for item in self._records() if item["profile_type"] == profile_type),
            None,
        )
        if not row or not row.get("credentials_encrypted"):
            return {}
        try:
            raw = self._cipher().decrypt(
                row["credentials_encrypted"].encode("ascii")
            )
            credentials = json.loads(raw.decode("utf-8"))
        except (InvalidToken, UnicodeError, json.JSONDecodeError, KeyError) as exc:
            raise ValueError("Saved credentials could not be decrypted.") from exc
        if not isinstance(credentials, dict):
            raise ValueError("Saved credentials are invalid.")
        return credentials

    def get_profile(self, profile_type):
        if profile_type not in self.PROFILE_TYPES:
            raise ValueError("Unknown database profile type.")
        if profile_type == "folder":
            path = get_active_data_dir()
            return {
                "path": str(path),
                "profile_type": "folder",
                "active": True,
            }
        row = next(
            (item for item in self._records() if item["profile_type"] == profile_type),
            None,
        )
        if not row:
            return None
        return {
            **{key: value for key, value in row["configuration"].items()
               if key in ({"host", "port", "database", "ssl_mode"} if profile_type == "mysql" else
                          {"service_name", "base_url", "api_version", "auth_type", "ca_certificate_path"})},
            "profile_type": profile_type,
            "credentials_configured": bool(row.get("credentials_encrypted")),
            "tested_at": row.get("tested_at", ""),
            "active": False,
            "status": "pending",
            "validation_scope": "mysql_connection" if profile_type == "mysql" else "https_transport_only",
            "activation_requirements": (
                "MySQL repository adapters and verified JSON data migration are required."
                if profile_type == "mysql" else
                "An API data contract, authentication test, repository adapter, and verified data migration are required."
            ),
        }

    @staticmethod
    def test_folder_access(path):
        folder = Path(str(path or "").strip()).expanduser()
        if not folder.is_absolute():
            raise ValueError("Enter an absolute server folder path.")
        if not folder.is_dir():
            raise ValueError("The folder does not exist or is not accessible.")
        try:
            with os.scandir(folder) as entries:
                next(entries, None)
        except OSError as exc:
            raise ValueError(
                "The application server cannot read this folder."
            ) from exc
        probe_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".db-access-test-",
                dir=folder,
                delete=False,
            ) as probe:
                probe_path = Path(probe.name)
                probe.write(b"folder access test")
                probe.flush()
                os.fsync(probe.fileno())
            if probe_path.read_bytes() != b"folder access test":
                raise OSError("Folder access read-back failed")
        except OSError as exc:
            raise ValueError(
                "The application server cannot write to this folder."
            ) from exc
        finally:
            if probe_path is not None:
                try:
                    probe_path.unlink(missing_ok=True)
                except OSError as exc:
                    raise ValueError(
                        "Could not remove the temporary folder access test file."
                    ) from exc
        return {"status": "success"}

    @classmethod
    def _normalize_mysql(cls, form):
        host = str(form.get("host", "")).strip()
        database = str(form.get("database", "")).strip()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        ssl_mode = str(form.get("ssl_mode", "PREFERRED")).strip().upper()
        try:
            raw_port = form.get("port", 3306)
            if isinstance(raw_port, bool) or isinstance(raw_port, float):
                raise ValueError("Invalid port")
            port = int(raw_port)
        except (TypeError, ValueError) as exc:
            raise ValueError("Port must be a number between 1 and 65535.") from exc
        if not host or not database:
            raise ValueError("Host and Database Name are required.")
        if not 1 <= port <= 65535:
            raise ValueError("Port must be a number between 1 and 65535.")
        if ssl_mode not in cls.SSL_MODES:
            raise ValueError("Select a valid SSL Mode.")
        return {
            "configuration": {
                "host": host,
                "port": port,
                "database": database,
                "ssl_mode": ssl_mode,
            },
            "credentials": {"username": username, "password": password},
        }

    @classmethod
    def _normalize_api(cls, form, *, allow_missing_credentials=False):
        service_name = str(form.get("service_name", "")).strip()
        base_url = str(form.get("base_url", "")).strip().rstrip("/")
        api_version = str(form.get("api_version", "")).strip()
        auth_type = str(form.get("auth_type", "")).strip()
        credentials = {}
        if not service_name or not base_url or not api_version:
            raise ValueError("Service Name, Base URL, and API Version are required.")
        if auth_type not in cls.AUTH_TYPES:
            raise ValueError("Select a valid Authentication Type.")

        if any(ord(char) < 32 for char in base_url):
            raise ValueError("Base URL contains invalid control characters.")
        parsed = urlsplit(base_url)
        if not parsed.hostname or parsed.scheme not in {"http", "https"}:
            raise ValueError("Base URL must be a valid HTTP or HTTPS URL.")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("Base URL must include a valid port.") from exc
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "Base URL must not contain credentials, query parameters, or fragments."
            )
        if parsed.scheme != "https":
            raise ValueError("Use HTTPS for API services.")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Base URL must include a valid port.")

        if auth_type == "API Key":
            credentials["api_key"] = str(form.get("api_key", "")).strip()
            if not credentials["api_key"] and not allow_missing_credentials:
                raise ValueError("API Key is required.")
        elif auth_type == "Bearer Token":
            credentials["token"] = str(form.get("token", "")).strip()
            if not credentials["token"] and not allow_missing_credentials:
                raise ValueError("Bearer Token is required.")
        elif auth_type == "Basic Auth":
            credentials["username"] = str(form.get("api_username", "")).strip()
            credentials["password"] = str(form.get("api_password", ""))
            if (
                not allow_missing_credentials
                and (not credentials["username"] or not credentials["password"])
            ):
                raise ValueError("Username and Password are required for Basic Auth.")

        ca_path = str(form.get("ca_certificate_path", "")).strip()
        if ca_path and not Path(ca_path).is_file():
            raise ValueError("The CA certificate is not available on the server.")
        return {
            "configuration": {
                "service_name": service_name,
                "base_url": base_url,
                "api_version": api_version,
                "auth_type": auth_type,
                "ca_certificate_path": ca_path,
            },
            "credentials": credentials,
        }

    @staticmethod
    def _probe_mysql(configuration, credentials):
        connect_args = {"connect_timeout": 8}
        ssl_mode = configuration["ssl_mode"]
        if ssl_mode == "DISABLED":
            connect_args["ssl_disabled"] = True
        elif ssl_mode == "REQUIRED":
            connect_args["ssl"] = {}
        elif ssl_mode == "VERIFY_CA":
            connect_args["ssl_verify_cert"] = True
        elif ssl_mode == "VERIFY_IDENTITY":
            connect_args["ssl_verify_cert"] = True
            connect_args["ssl_verify_identity"] = True

        engine = None
        try:
            engine = create_engine(
                URL.create(
                    "mysql+pymysql",
                    username=credentials["username"],
                    password=credentials["password"],
                    host=configuration["host"],
                    port=configuration["port"],
                    database=configuration["database"],
                ),
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_recycle=300,
                hide_parameters=True,
            )
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, ValueError) as exc:
            raise ValueError(
                f"MySQL connection test failed ({type(exc).__name__})."
            ) from None
        finally:
            if engine is not None:
                engine.dispose()

    @staticmethod
    def _probe_api(base_url, ca_certificate_path=""):
        parsed = urlsplit(base_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((parsed.hostname, port), timeout=8) as raw:
                if parsed.scheme == "https":
                    context = ssl.create_default_context(
                        cafile=ca_certificate_path or None
                    )
                    with context.wrap_socket(
                        raw, server_hostname=parsed.hostname
                    ):
                        pass
        except (OSError, ssl.SSLError, ValueError) as exc:
            raise ValueError(
                f"API endpoint transport test failed ({type(exc).__name__})."
            ) from None

    def test_mysql_connection(self, form):
        normalized = self._normalize_mysql(form)
        credentials = self._credentials("mysql")
        for key, value in normalized["credentials"].items():
            if value:
                credentials[key] = value
        if not credentials.get("username"):
            raise ValueError("Username is required.")
        if not credentials.get("password"):
            raise ValueError("Password is required.")
        self._probe_mysql(normalized["configuration"], credentials)
        return {"status": "success"}

    def test_api_connection(self, form):
        normalized = self._normalize_api(form, allow_missing_credentials=True)
        credentials = normalized["credentials"]
        saved_credentials = self._credentials("api")
        for key, value in saved_credentials.items():
            if not credentials.get(key):
                credentials[key] = value
        required = {
            "API Key": ("api_key",),
            "Bearer Token": ("token",),
            "Basic Auth": ("username", "password"),
            "None": (),
        }[normalized["configuration"]["auth_type"]]
        missing_labels = {
            "api_key": "API Key",
            "token": "Bearer Token",
            "username": "Username",
            "password": "Password",
        }
        missing = [missing_labels[key] for key in required if not credentials.get(key)]
        if missing:
            label = " and ".join(missing)
            verb = "is" if len(missing) == 1 else "are"
            raise ValueError(f"{label} {verb} required.")
        self._probe_api(
            normalized["configuration"]["base_url"],
            normalized["configuration"]["ca_certificate_path"],
        )
        return {"status": "success"}

    def save_profile(self, profile_type, form):
        """Retest profiles and activate only the app's JSON folder."""
        if profile_type == "folder":
            active_path = self.activate_data_folder(form.get("path", ""))
            return {
                "path": str(active_path),
                "profile_type": "folder",
                "active": True,
            }
        elif profile_type == "mysql":
            self.test_mysql_connection(form)
            normalized = self._normalize_mysql(form)
            configuration = normalized["configuration"]
            credentials = normalized["credentials"]
            saved_credentials = self._credentials("mysql")
            for key, value in saved_credentials.items():
                if not credentials.get(key):
                    credentials[key] = value
        elif profile_type == "api":
            self.test_api_connection(form)
            normalized = self._normalize_api(form, allow_missing_credentials=True)
            configuration = normalized["configuration"]
            credentials = normalized["credentials"]
            saved_credentials = self._credentials("api")
            for key, value in saved_credentials.items():
                if not credentials.get(key):
                    credentials[key] = value
            auth_type = configuration["auth_type"]
            allowed = {
                "API Key": {"api_key"},
                "Bearer Token": {"token"},
                "Basic Auth": {"username", "password"},
                "None": set(),
            }[auth_type]
            credentials = {
                key: value for key, value in credentials.items() if key in allowed
            }
        else:
            raise ValueError("Unknown database profile type.")

        encrypted_credentials = ""
        if credentials:
            encrypted_credentials = self._cipher().encrypt(
                json.dumps(credentials, ensure_ascii=False).encode("utf-8")
            ).decode("ascii")

        record = {
            "profile_type": profile_type,
            "configuration": configuration,
            "credentials_encrypted": encrypted_credentials,
            "tested_at": datetime.now(timezone.utc).isoformat(),
            "active": False,
            "status": "pending",
        }
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            rows = self._records()
            updated = [row for row in rows if row["profile_type"] != profile_type]
            updated.append(record)
            JSONRepository(self.config_path).save_all(updated)
        return self.get_profile(profile_type)

    @staticmethod
    def _digest(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _validate_json_file(path):
        if path.suffix.lower() != ".json":
            return
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                json.load(file)
        except (ValueError, UnicodeError):
            raise ValueError(f"Invalid JSON data file: {path.name}. Current storage was not changed.") from None

    @staticmethod
    def _check_target(destination, target):
        if not target.resolve(strict=False).is_relative_to(destination):
            raise ValueError("Migration target leaves the selected folder.")
        for candidate in (target, *target.parents):
            if candidate == destination.parent:
                break
            if candidate.is_symlink():
                raise ValueError("Migration cannot use linked destination files or folders.")
        if target.exists() and not target.is_file():
            raise ValueError(f"Destination is not a file: {target.name}.")

    @staticmethod
    def _publish_staged_file(staged, destination, created):
        # Exclusive create: never replace a file that appeared after preflight.
        with destination.open("xb") as output:
            created.append((destination, destination.stat().st_ino))
            with staged.open("rb") as source:
                shutil.copyfileobj(source, output)
            output.flush()
            os.fsync(output.fileno())

    def _write_migration_manifest(self, path, value):
        from backend.data_paths import _atomic_migration_json
        _atomic_migration_json(path, value)

    def activate_data_folder(self, path):
        """Back up, stage, verify, then atomically activate JSON storage."""
        self.test_folder_access(path)
        destination = Path(str(path).strip()).expanduser().resolve()
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        # The same project-wide lock protects repository writes and path switches.
        with _PERSISTENCE_LOCK:
            source = get_active_data_dir().resolve()
            if source == destination:
                return destination
            if not source.is_dir():
                raise ValueError("The current active data folder is unavailable; migration was not started.")
            if source in destination.parents or destination in source.parents:
                raise ValueError("Choose a data folder that is not inside or above the current data folder.")
            files = []
            for item in source.rglob("*"):
                relative = item.relative_to(source)
                if relative.parts[0] in STABLE_DATA_DIRECTORIES:
                    continue
                if len(relative.parts) == 1 and relative.name in STABLE_DATA_FILES:
                    continue
                if item.is_symlink():
                    raise ValueError(f"Cannot migrate linked data file: {relative.as_posix()}.")
                if item.is_file():
                    self._validate_json_file(item)
                    files.append((item, relative))
            conflicts = []
            for item, relative in files:
                target = destination / relative
                self._check_target(destination, target)
                if target.exists() and not data_files_equal(item, target):
                    conflicts.append(relative.as_posix())
            if conflicts:
                raise ValueError("The selected folder contains files that differ from current data: "
                                 + ", ".join(conflicts[:5])
                                 + ". No files were replaced and the active folder was not changed.")
            recovery = self.data_dir / ".storage_migrations" / uuid.uuid4().hex
            backup = recovery / "backup"
            staged = recovery / "staged"
            backup.mkdir(parents=True, mode=0o700)
            staged.mkdir(mode=0o700)
            manifest = {"source": str(source), "destination": str(destination),
                        "status": "staging", "files": {}}
            manifest_path = recovery / "manifest.json"
            self._write_migration_manifest(manifest_path, manifest)
            created = []
            switched = False
            try:
                for item, relative in files:
                    original_digest = self._digest(item)
                    for directory in (backup, staged):
                        copy = directory / relative
                        copy.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, copy)
                        if self._digest(copy) != original_digest:
                            raise ValueError(f"Migration copy verification failed: {relative.as_posix()}.")
                    manifest["files"][relative.as_posix()] = original_digest
                manifest["status"] = "backup_verified"
                self._write_migration_manifest(manifest_path, manifest)
                for item, relative in files:
                    target = destination / relative
                    self._check_target(destination, target)
                    if target.exists():
                        if not data_files_equal(staged / relative, target):
                            raise ValueError(f"Destination changed during migration: {relative.as_posix()}.")
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self._publish_staged_file(staged / relative, target, created)
                # Revalidate the full snapshot, not just successful copy calls.
                for item, relative in files:
                    if self._digest(item) != manifest["files"][relative.as_posix()]:
                        raise ValueError(f"Source changed during migration: {relative.as_posix()}.")
                    if not data_files_equal(staged / relative, destination / relative):
                        raise ValueError(f"Destination verification failed: {relative.as_posix()}.")
                manifest["status"] = "verified_ready_to_activate"
                self._write_migration_manifest(manifest_path, manifest)
                # Last fallible step: current configuration remains intact if it fails.
                save_active_data_dir(destination)
                switched = True
                manifest["status"] = "activated"
                try:
                    self._write_migration_manifest(manifest_path, manifest)
                except OSError:
                    pass  # Active configuration is authoritative if this final annotation fails.
            except (OSError, ValueError) as exc:
                if not switched:
                    for target, inode in reversed(created):
                        # Remove only files exclusively created by this operation.
                        if (target.resolve(strict=False).is_relative_to(destination)
                                and not target.is_symlink() and target.exists()
                                and target.stat().st_ino == inode):
                            try:
                                target.unlink()
                            except OSError:
                                pass  # Recovery manifest and backup remain available.
                    manifest["status"] = "failed_current_storage_unchanged"
                    try:
                        self._write_migration_manifest(manifest_path, manifest)
                    except OSError:
                        pass
                raise ValueError(f"Folder migration failed; current storage is unchanged. "
                                 f"Backup and recovery details: {recovery}. "
                                 f"Reason: {type(exc).__name__}.") from None
            return destination

    def store_ca_certificate(self, filename, content):
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pem", ".crt", ".cer"}:
            raise ValueError("Upload a PEM or CRT CA certificate.")
        if not content or len(content) > self.MAX_CERTIFICATE_BYTES:
            raise ValueError("The CA certificate must be under 1 MB.")
        try:
            try:
                x509.load_pem_x509_certificate(content)
            except ValueError:
                x509.load_der_x509_certificate(content)
        except ValueError as exc:
            raise ValueError("The uploaded file is not a valid X.509 certificate.") from exc

        self.certificate_dir.mkdir(parents=True, exist_ok=True)
        destination = self.certificate_dir / f"{uuid.uuid4().hex}{suffix}"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.certificate_dir,
                prefix=destination.name + ".",
                suffix=".tmp",
                delete=False,
            ) as uploaded:
                temporary = Path(uploaded.name)
                uploaded.write(content)
                uploaded.flush()
                os.fsync(uploaded.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return str(destination)

    @staticmethod
    def browse_directories(path):
        folder = Path(path).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError("Choose an accessible server directory.")
        try:
            entries = sorted(
                (
                    {"name": child.name, "path": str(child)}
                    for child in folder.iterdir()
                    if child.is_dir()
                ),
                key=lambda entry: entry["name"].casefold(),
            )
        except OSError as exc:
            raise ValueError("The application server cannot list this directory.") from exc
        return {
            "path": str(folder),
            "parent": str(folder.parent) if folder.parent != folder else "",
            "entries": entries[:100],
        }

    @staticmethod
    def browse_native_folder(path):
        """Open a Windows folder picker when the console server has a desktop."""
        if platform.system() != "Windows":
            return None

        import ctypes
        from ctypes import wintypes

        class BrowseInfo(ctypes.Structure):
            _fields_ = [
                ("owner", wintypes.HWND),
                ("root", ctypes.c_void_p),
                ("display_name", wintypes.LPWSTR),
                ("title", wintypes.LPCWSTR),
                ("flags", wintypes.UINT),
                ("callback", ctypes.c_void_p),
                ("parameter", wintypes.LPARAM),
                ("image", ctypes.c_int),
            ]

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.LPARAM,
            wintypes.LPARAM,
        )
        browse_initialized = 1
        set_initial_selection = 0x0400 + 103
        return_only_file_system_directories = 0x0001
        new_dialog_style = 0x0040
        start = Path(path).expanduser()
        initial_dir = start if start.is_dir() else DEFAULT_DATA_DIR
        initial_path = ctypes.create_unicode_buffer(str(initial_dir))

        def set_initial_folder(window, message, _parameter, _data):
            if message == browse_initialized:
                user.SendMessageW(
                    window,
                    set_initial_selection,
                    1,
                    ctypes.cast(initial_path, ctypes.c_void_p).value,
                )
            return 0

        callback = callback_type(set_initial_folder)
        ole = None
        com_initialized = False
        try:
            shell = ctypes.WinDLL("shell32", use_last_error=True)
            ole = ctypes.WinDLL("ole32", use_last_error=True)
            user = ctypes.WinDLL("user32", use_last_error=True)
            shell.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BrowseInfo)]
            shell.SHBrowseForFolderW.restype = ctypes.c_void_p
            shell.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
            shell.SHGetPathFromIDListW.restype = wintypes.BOOL
            user.SendMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            ole.CoInitialize.restype = ctypes.c_long
            result = ole.CoInitialize(None)
            if result < 0:
                return None
            com_initialized = True
            info = BrowseInfo(
                owner=user.GetDesktopWindow(),
                root=None,
                display_name=ctypes.create_unicode_buffer(32768),
                title="Select JSON data folder",
                flags=(
                    return_only_file_system_directories
                    | new_dialog_style
                ),
                callback=ctypes.cast(callback, ctypes.c_void_p),
                parameter=0,
                image=0,
            )
            item = shell.SHBrowseForFolderW(ctypes.byref(info))
            if not item:
                return ""
            try:
                selected_path = ctypes.create_unicode_buffer(32768)
                if not shell.SHGetPathFromIDListW(item, selected_path):
                    return None
                return str(Path(selected_path.value).resolve())
            finally:
                ole.CoTaskMemFree(item)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
        finally:
            if com_initialized:
                ole.CoUninitialize()
