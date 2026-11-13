"""MySQL persistence adapter that preserves the JSON repository interface."""

import hashlib
import json
import threading
from pathlib import Path

from cryptography.fernet import InvalidToken
from sqlalchemy import Column, DateTime, JSON, MetaData, String, Table, func, insert, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine

from backend.data_paths import DEFAULT_DATA_DIR
from backend.services.credential_encryption import get_credential_cipher


CONFIGURATION_FILE = DEFAULT_DATA_DIR / "database_configurations.json"
_ENGINE_LOCK = threading.RLock()
_ENGINES: dict[str, Engine] = {}
_SCHEMA_READY: set[str] = set()
_METADATA = MetaData()
_DOCUMENTS = Table(
    "application_json_documents",
    _METADATA,
    Column("document_id", String(64), primary_key=True),
    Column("document_key", String(1024), nullable=False),
    Column("payload", JSON, nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    ),
)


def _active_mysql_configuration() -> dict | None:
    if not CONFIGURATION_FILE.exists():
        return None
    try:
        rows = json.loads(CONFIGURATION_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Database configuration cannot be read.") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Database configuration is invalid.")

    profile = next(
        (
            row for row in rows
            if row.get("profile_type") == "mysql" and row.get("active") is True
        ),
        None,
    )
    if profile is None:
        return None

    configuration = profile.get("configuration")
    encrypted = profile.get("credentials_encrypted")
    if not isinstance(configuration, dict) or not isinstance(encrypted, str) or not encrypted:
        raise ValueError("The active MySQL configuration is incomplete.")
    try:
        credentials = json.loads(
            get_credential_cipher().decrypt(encrypted.encode("ascii")).decode("utf-8")
        )
    except (InvalidToken, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("The active MySQL credentials could not be decrypted.") from exc
    if not isinstance(credentials, dict):
        raise ValueError("The active MySQL credentials are invalid.")

    required = ("host", "port", "database", "ssl_mode")
    if any(not configuration.get(key) for key in required):
        raise ValueError("The active MySQL configuration is incomplete.")
    if not credentials.get("username") or not credentials.get("password"):
        raise ValueError("The active MySQL credentials are incomplete.")
    return {**configuration, **credentials}


def _connect_args(configuration: dict) -> dict:
    ssl_mode = configuration["ssl_mode"]
    connect_args = {"connect_timeout": 8}
    if ssl_mode == "DISABLED":
        connect_args["ssl_disabled"] = True
    elif ssl_mode == "REQUIRED":
        connect_args["ssl"] = {}
    elif ssl_mode == "VERIFY_CA":
        connect_args["ssl_verify_cert"] = True
    elif ssl_mode == "VERIFY_IDENTITY":
        connect_args["ssl_verify_cert"] = True
        connect_args["ssl_verify_identity"] = True
    return connect_args


def _engine_fingerprint(configuration: dict) -> str:
    return hashlib.sha256(
        json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _engine_for(configuration: dict) -> Engine:
    fingerprint = _engine_fingerprint(configuration)
    with _ENGINE_LOCK:
        engine = _ENGINES.get(fingerprint)
        if engine is None:
            engine = create_engine(
                URL.create(
                    "mysql+pymysql",
                    username=configuration["username"],
                    password=configuration["password"],
                    host=configuration["host"],
                    port=int(configuration["port"]),
                    database=configuration["database"],
                ),
                connect_args=_connect_args(configuration),
                pool_pre_ping=True,
                pool_recycle=300,
                hide_parameters=True,
            )
            _ENGINES[fingerprint] = engine
        return engine


def active_mysql_store() -> "MySQLJSONStore | None":
    configuration = _active_mysql_configuration()
    return MySQLJSONStore(configuration) if configuration else None


class MySQLJSONStore:
    def __init__(self, configuration: dict, engine: Engine | None = None):
        self.configuration = dict(configuration)
        self.engine = engine or _engine_for(self.configuration)
        self._fingerprint = (
            _engine_fingerprint(self.configuration) if engine is None else None
        )

    @staticmethod
    def document_id(document_key: str) -> str:
        return hashlib.sha256(document_key.encode("utf-8")).hexdigest()

    def ensure_schema(self) -> None:
        if self._fingerprint and self._fingerprint in _SCHEMA_READY:
            return
        try:
            _METADATA.create_all(self.engine, checkfirst=True)
            if self._fingerprint:
                _SCHEMA_READY.add(self._fingerprint)
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL application storage could not be initialized ({type(exc).__name__})."
            ) from None

    def get_document(self, document_key: str, default=None):
        self.ensure_schema()
        statement = select(_DOCUMENTS.c.payload).where(
            _DOCUMENTS.c.document_id == self.document_id(document_key)
        )
        try:
            with self.engine.connect() as connection:
                payload = connection.execute(statement).scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL data could not be read ({type(exc).__name__})."
            ) from None
        if payload is None:
            return default
        return payload

    def has_document(self, document_key: str) -> bool:
        self.ensure_schema()
        statement = select(_DOCUMENTS.c.document_id).where(
            _DOCUMENTS.c.document_id == self.document_id(document_key)
        )
        try:
            with self.engine.connect() as connection:
                return connection.execute(statement).scalar_one_or_none() is not None
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL data could not be checked ({type(exc).__name__})."
            ) from None

    def save_document(self, document_key: str, payload) -> None:
        try:
            json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("MySQL application data must be valid JSON.") from exc
        self.ensure_schema()
        values = {
            "document_id": self.document_id(document_key),
            "document_key": document_key,
            "payload": payload,
        }
        try:
            with self.engine.begin() as connection:
                existing_key = connection.execute(
                    select(_DOCUMENTS.c.document_key).where(
                        _DOCUMENTS.c.document_id == values["document_id"]
                    )
                ).scalar_one_or_none()
                if existing_key is not None and existing_key != document_key:
                    raise ValueError("MySQL application storage key collision detected.")
                if self.engine.dialect.name == "mysql":
                    statement = mysql_insert(_DOCUMENTS).values(**values)
                    statement = statement.on_duplicate_key_update(
                        document_key=statement.inserted.document_key,
                        payload=statement.inserted.payload,
                        updated_at=func.current_timestamp(),
                    )
                    connection.execute(statement)
                else:
                    existing = connection.execute(
                        select(_DOCUMENTS.c.document_id).where(
                            _DOCUMENTS.c.document_id == values["document_id"]
                        )
                    ).scalar_one_or_none()
                    if existing:
                        connection.execute(
                            update(_DOCUMENTS)
                            .where(_DOCUMENTS.c.document_id == values["document_id"])
                            .values(document_key=document_key, payload=payload)
                        )
                    else:
                        connection.execute(insert(_DOCUMENTS).values(**values))
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL data could not be saved ({type(exc).__name__})."
            ) from None

    def list_documents(self) -> list[tuple[str, object]]:
        self.ensure_schema()
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(_DOCUMENTS.c.document_key, _DOCUMENTS.c.payload)
                ).all()
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL data could not be listed ({type(exc).__name__})."
            ) from None
        return [(key, payload) for key, payload in rows]

    def import_documents(self, documents: list[tuple[str, object]]) -> None:
        """Import without replacing non-empty target data."""
        self.ensure_schema()
        try:
            with self.engine.begin() as connection:
                existing_rows = connection.execute(
                    select(_DOCUMENTS.c.document_id, _DOCUMENTS.c.document_key, _DOCUMENTS.c.payload)
                ).all()
                existing = {row.document_id: row for row in existing_rows}
                additions = []
                updates = []
                for document_key, payload in documents:
                    document_id = self.document_id(document_key)
                    target = existing.get(document_id)
                    if target is None:
                        additions.append({
                            "document_id": document_id,
                            "document_key": document_key,
                            "payload": payload,
                        })
                    elif target.document_key != document_key:
                        raise ValueError("MySQL application storage key collision detected.")
                    elif target.payload != payload and target.payload in ([], {}) and payload:
                        updates.append((document_id, payload))
                    elif target.payload != payload and payload:
                        raise ValueError(
                            f"MySQL already contains different data for {Path(document_key).name}; "
                            "nothing was overwritten."
                        )
                if additions:
                    connection.execute(insert(_DOCUMENTS), additions)
                for document_id, payload in updates:
                    connection.execute(
                        update(_DOCUMENTS)
                        .where(_DOCUMENTS.c.document_id == document_id)
                        .values(payload=payload, updated_at=func.current_timestamp())
                    )
        except SQLAlchemyError as exc:
            raise ValueError(
                f"MySQL data migration failed ({type(exc).__name__}); "
                "the current storage remains active."
            ) from None
