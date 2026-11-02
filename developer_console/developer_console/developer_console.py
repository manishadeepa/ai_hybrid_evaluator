import hmac
import asyncio
import os
import sys
from pathlib import Path

import reflex as rx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.group_admin_service import GroupAdminService
from backend.services.database_configuration_service import (
    DEFAULT_DATA_DIR,
    PROJECT_ROOT,
    DatabaseConfigurationService,
)
from backend.data_paths import get_active_data_dir
from backend.services.master_admin_service import MasterAdminService

load_dotenv(PROJECT_ROOT / "developer_console" / ".env")


class State(rx.State):
    is_authenticated: bool = False
    login_error: str = ""
    show_password: bool = False
    active_section: str = "overview"
    database_view: str = "overview"
    database_error: str = ""
    database_message: str = ""
    database_test_status: str = "Not tested yet"
    active_storage_status: str = f"Active JSON data folder: {DEFAULT_DATA_DIR}"

    folder_path: str = str(DEFAULT_DATA_DIR)
    folder_browser_open: bool = False
    folder_browser_path: str = ""
    folder_browser_parent: str = ""
    folder_browser_entries: list[dict[str, str]] = []
    folder_browser_error: str = ""

    mysql_host: str = ""
    mysql_port: str = "3306"
    mysql_database: str = ""
    mysql_username: str = ""
    mysql_password: str = ""
    mysql_ssl_mode: str = "PREFERRED"
    show_mysql_password: bool = False
    mysql_credentials_configured: bool = False

    api_service_name: str = ""
    api_base_url: str = ""
    api_version: str = "v1"
    api_auth_type: str = "API Key"
    api_key: str = ""
    api_token: str = ""
    api_username: str = ""
    api_password: str = ""
    show_api_credential: bool = False
    api_credentials_configured: bool = False
    api_ca_certificate_path: str = ""
    master_admin: dict[str, str] = {"username": ""}
    admin_management_error: str = ""
    admin_management_message: str = ""

    new_master_admin_username: str = ""
    new_master_admin_password: str = ""
    new_master_admin_confirm_password: str = ""
    show_new_master_admin_password: bool = False
    show_new_master_admin_confirm_password: bool = False

    show_edit_master_admin_dialog: bool = False
    edit_master_admin_username: str = ""
    show_reset_master_admin_dialog: bool = False
    reset_master_admin_password: str = ""
    reset_master_admin_confirm_password: str = ""
    show_reset_master_admin_password: bool = False
    show_reset_master_admin_confirm_password: bool = False

    def _is_developer_authenticated(self) -> bool:
        if self.is_authenticated:
            return True
        self.admin_management_error = "Sign in to the developer console to manage administrators."
        return False

    def _clear_admin_management_forms(self):
        self.new_master_admin_username = ""
        self.new_master_admin_password = ""
        self.new_master_admin_confirm_password = ""
        self.show_new_master_admin_password = False
        self.show_new_master_admin_confirm_password = False
        self.show_edit_master_admin_dialog = False
        self.edit_master_admin_username = ""
        self.show_reset_master_admin_dialog = False
        self.reset_master_admin_password = ""
        self.reset_master_admin_confirm_password = ""
        self.show_reset_master_admin_password = False
        self.show_reset_master_admin_confirm_password = False

    def login(self, form_data: dict):
        expected_username = os.environ.get("DEV_CONSOLE_USERNAME", "")
        expected_password = os.environ.get("DEV_CONSOLE_PASSWORD", "")
        username = str(form_data.get("username", ""))
        password = str(form_data.get("password", ""))

        if not expected_username or not expected_password:
            self.login_error = "Developer-console credentials are not configured."
            return

        if hmac.compare_digest(username, expected_username) and hmac.compare_digest(
            password, expected_password
        ):
            self.is_authenticated = True
            self.login_error = ""
        else:
            self.login_error = "Username or password is incorrect."

    def toggle_password(self):
        self.show_password = not self.show_password

    def navigate(self, section: str):
        if not self._is_developer_authenticated():
            return
        self.active_section = section
        if section == "admins":
            self.load_admin_accounts()
        elif section == "database":
            self.database_view = "overview"
            self.database_error = ""
            self.database_message = ""
            self.active_storage_status = (
                f"Active JSON data folder: {get_active_data_dir()}"
            )

    def _require_database_access(self) -> bool:
        if self.is_authenticated:
            return True
        self.database_error = "Sign in to the developer console to manage database settings."
        return False

    def open_database_form(self, profile_type: str):
        if not self._require_database_access():
            return
        if profile_type not in DatabaseConfigurationService.PROFILE_TYPES:
            self.database_error = "Unknown database configuration."
            return
        try:
            profile = DatabaseConfigurationService().get_profile(profile_type) or {}
        except (OSError, ValueError) as exc:
            self.database_error = f"Unable to load saved configuration: {exc}"
            return
        self.database_view = profile_type
        self.database_error = ""
        self.database_message = ""
        self.database_test_status = "Not tested yet"
        if profile_type == "folder":
            self.folder_path = profile.get("path", str(DEFAULT_DATA_DIR))
            self.active_storage_status = (
                f"Active JSON data folder: {self.folder_path}"
            )
        elif profile_type == "mysql":
            self.mysql_host = profile.get("host", "")
            self.mysql_port = str(profile.get("port", 3306))
            self.mysql_database = profile.get("database", "")
            self.mysql_username = ""
            self.mysql_ssl_mode = profile.get("ssl_mode", "PREFERRED")
            self.mysql_password = ""
            self.mysql_credentials_configured = profile.get(
                "credentials_configured", False
            )
            self.show_mysql_password = False
        else:
            self.api_service_name = profile.get("service_name", "")
            self.api_base_url = profile.get("base_url", "")
            self.api_version = profile.get("api_version", "v1")
            self.api_auth_type = profile.get("auth_type", "API Key")
            self.api_ca_certificate_path = profile.get(
                "ca_certificate_path", ""
            )
            self.api_key = ""
            self.api_token = ""
            self.api_username = ""
            self.api_password = ""
            self.api_credentials_configured = profile.get(
                "credentials_configured", False
            )
            self.show_api_credential = False

    def back_to_database_management(self):
        if not self._require_database_access():
            return
        self.database_view = "overview"
        self.database_error = ""
        self.database_message = ""
        self.mysql_password = ""
        self.api_key = ""
        self.api_token = ""
        self.api_username = ""
        self.api_password = ""

    def set_folder_path(self, value: str):
        self.folder_path = value
        self.database_error = ""
        self.database_test_status = "Not tested yet"

    async def open_folder_browser(self):
        if not self._require_database_access():
            return
        start = Path(self.folder_path).expanduser()
        if not start.is_dir():
            start = PROJECT_ROOT

        self.folder_browser_open = False
        self.folder_browser_error = ""
        self.database_error = ""
        self.database_message = ""
        try:
            selected = await asyncio.to_thread(
                DatabaseConfigurationService.browse_native_folder,
                str(start),
            )
        except (OSError, RuntimeError) as exc:
            self.folder_browser_error = (
                f"Native folder picker could not be opened: {exc}"
            )
            selected = None

        if selected is not None:
            if selected:
                self.folder_path = selected
                self.database_error = ""
                self.database_test_status = "Not tested yet"
            return

        self._load_folder_browser_directory(start)
        if not self.folder_browser_error:
            self.folder_browser_open = True
            self.database_message = (
                "The native folder picker is unavailable; use the in-app server-folder browser."
            )

    def _load_folder_browser_directory(self, path):
        try:
            browser = DatabaseConfigurationService.browse_directories(path)
        except (OSError, ValueError) as exc:
            self.folder_browser_error = str(exc)
            return
        self.folder_browser_path = browser["path"]
        self.folder_browser_parent = browser["parent"]
        self.folder_browser_entries = browser["entries"]
        self.folder_browser_error = ""

    def browse_folder_directory(self, path: str):
        if not self._require_database_access():
            return
        self._load_folder_browser_directory(path)

    def browse_folder_parent(self):
        if not self._require_database_access():
            return
        if self.folder_browser_parent:
            self._load_folder_browser_directory(self.folder_browser_parent)

    def select_folder_browser_path(self):
        if not self._require_database_access():
            return
        self.folder_path = self.folder_browser_path
        self.folder_browser_open = False
        self.database_error = ""
        self.database_test_status = "Not tested yet"

    def close_folder_browser(self):
        self.folder_browser_open = False
        self.folder_browser_error = ""

    def set_folder_browser_open(self, is_open: bool):
        self.folder_browser_open = is_open
        if not is_open:
            self.folder_browser_error = ""

    async def test_folder_access(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            await asyncio.to_thread(
                DatabaseConfigurationService.test_folder_access, self.folder_path
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "Folder access failed"
            self.database_error = str(exc)
            return
        self.database_test_status = "Folder access verified"
        self.database_message = (
            "The application server can read and write this folder. "
            "It will be migrated and activated only after Save and Use."
        )

    async def save_folder_configuration(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            saved_profile = await asyncio.to_thread(
                DatabaseConfigurationService().save_profile,
                "folder",
                {"path": self.folder_path},
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "Folder activation failed; current folder unchanged"
            self.database_error = str(exc)
            return
        active_path = saved_profile["path"]
        self.active_storage_status = f"Active JSON data folder: {active_path}"
        self.folder_path = active_path
        self.database_test_status = "Folder path migrated and active"
        self.database_message = (
            "The JSON data folder is active. Existing source files were left in place; "
            "matching files were reused and conflicting files were not overwritten."
        )

    def set_mysql_host(self, value: str):
        self.mysql_host = value
        self._reset_database_test()

    def set_mysql_port(self, value: str):
        self.mysql_port = value
        self._reset_database_test()

    def set_mysql_database(self, value: str):
        self.mysql_database = value
        self._reset_database_test()

    def set_mysql_username(self, value: str):
        self.mysql_username = value
        self._reset_database_test()

    def set_mysql_password(self, value: str):
        self.mysql_password = value
        self._reset_database_test()

    def set_mysql_ssl_mode(self, value: str):
        self.mysql_ssl_mode = value
        self._reset_database_test()

    def toggle_mysql_password(self):
        self.show_mysql_password = not self.show_mysql_password

    def _mysql_form(self):
        return {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "database": self.mysql_database,
            "username": self.mysql_username,
            "password": self.mysql_password,
            "ssl_mode": self.mysql_ssl_mode,
        }

    async def test_mysql_connection(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            await asyncio.to_thread(
                DatabaseConfigurationService().test_mysql_connection,
                self._mysql_form(),
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "MySQL connection failed"
            self.database_error = str(exc)
            return
        self.database_test_status = "MySQL connection verified"
        self.database_message = "Connection verified. No storage settings were changed."

    async def save_mysql_configuration(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            await asyncio.to_thread(
                DatabaseConfigurationService().save_profile,
                "mysql",
                self._mysql_form(),
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "MySQL connection failed"
            self.database_error = str(exc)
            return
        self.mysql_username = ""
        self.mysql_password = ""
        self.mysql_credentials_configured = True
        self.database_test_status = "MySQL connection verified and saved (not active)"
        self.database_message = (
            "Credentials were saved encrypted. JSON file storage remains active; "
            "no data migration or backend switch was performed."
        )

    def set_api_service_name(self, value: str):
        self.api_service_name = value
        self._reset_database_test()

    def set_api_base_url(self, value: str):
        self.api_base_url = value
        self._reset_database_test()

    def set_api_version(self, value: str):
        self.api_version = value
        self._reset_database_test()

    def set_api_auth_type(self, value: str):
        self.api_auth_type = value
        self.api_key = ""
        self.api_token = ""
        self.api_username = ""
        self.api_password = ""
        self.show_api_credential = False
        self._reset_database_test()

    def set_api_key(self, value: str):
        self.api_key = value
        self._reset_database_test()

    def set_api_token(self, value: str):
        self.api_token = value
        self._reset_database_test()

    def set_api_username(self, value: str):
        self.api_username = value
        self._reset_database_test()

    def set_api_password(self, value: str):
        self.api_password = value
        self._reset_database_test()

    def set_api_ca_certificate_path(self, value: str):
        self.api_ca_certificate_path = value
        self._reset_database_test()

    def toggle_api_credential_visibility(self):
        self.show_api_credential = not self.show_api_credential

    def _api_form(self):
        return {
            "service_name": self.api_service_name,
            "base_url": self.api_base_url,
            "api_version": self.api_version,
            "auth_type": self.api_auth_type,
            "api_key": self.api_key,
            "token": self.api_token,
            "api_username": self.api_username,
            "api_password": self.api_password,
            "ca_certificate_path": self.api_ca_certificate_path,
        }

    async def handle_ca_certificate_upload(self, files: list[rx.UploadFile]):
        if not self._require_database_access():
            return
        try:
            if len(files) != 1:
                raise ValueError("Select exactly one CA certificate.")
            content = await files[0].read()
            path = await asyncio.to_thread(
                DatabaseConfigurationService().store_ca_certificate,
                files[0].filename,
                content,
            )
        except (OSError, ValueError) as exc:
            self.database_error = str(exc)
            return
        self.api_ca_certificate_path = path
        self.database_error = ""
        self.database_test_status = "Not tested yet"
        self.database_message = "CA certificate uploaded to the application server."

    async def test_api_connection(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            await asyncio.to_thread(
                DatabaseConfigurationService().test_api_connection,
                self._api_form(),
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "API transport test failed"
            self.database_error = str(exc)
            return
        self.database_test_status = "API endpoint transport verified"
        self.database_message = (
            "HTTPS transport is reachable. No API credentials or data endpoints were "
            "tested because no API contract is configured."
        )

    async def save_api_configuration(self):
        if not self._require_database_access():
            return
        self.database_error = ""
        self.database_message = ""
        try:
            await asyncio.to_thread(
                DatabaseConfigurationService().save_profile,
                "api",
                self._api_form(),
            )
        except (OSError, ValueError) as exc:
            self.database_test_status = "API transport test failed"
            self.database_error = str(exc)
            return
        self.api_key = ""
        self.api_token = ""
        self.api_username = ""
        self.api_password = ""
        self.api_credentials_configured = self.api_auth_type != "None"
        self.database_test_status = "API transport verified and profile saved (not active)"
        self.database_message = (
            "Credentials were saved encrypted. JSON file storage remains active, and "
            "no API endpoint or data contract was invented."
        )

    def _reset_database_test(self):
        self.database_error = ""
        self.database_message = ""
        self.database_test_status = "Not tested yet"

    def load_admin_accounts(self):
        if not self._is_developer_authenticated():
            return
        self.admin_management_error = ""
        self.admin_management_message = ""
        try:
            master_admin = MasterAdminService().get() or {"username": ""}
        except (OSError, ValueError) as exc:
            self.admin_management_error = f"Unable to load administrator accounts: {exc}"
            return

        self.master_admin = master_admin

    def set_new_master_admin_username(self, value: str):
        self.new_master_admin_username = value
        self.admin_management_error = ""

    def set_new_master_admin_password(self, value: str):
        self.new_master_admin_password = value
        self.admin_management_error = ""

    def set_new_master_admin_confirm_password(self, value: str):
        self.new_master_admin_confirm_password = value
        self.admin_management_error = ""

    def toggle_new_master_admin_password(self):
        self.show_new_master_admin_password = not self.show_new_master_admin_password

    def toggle_new_master_admin_confirm_password(self):
        self.show_new_master_admin_confirm_password = (
            not self.show_new_master_admin_confirm_password
        )

    def create_master_admin(self):
        if not self._is_developer_authenticated():
            return
        username = self.new_master_admin_username.strip()
        password = self.new_master_admin_password.strip()
        confirm_password = self.new_master_admin_confirm_password.strip()
        if not username or not password or not confirm_password:
            self.admin_management_error = (
                "Username and both password fields are required."
            )
            return
        if password != confirm_password:
            self.admin_management_error = "Passwords do not match."
            return
        try:
            if any(
                row["username"].casefold() == username.casefold()
                for row in GroupAdminService().get_all()
            ):
                raise ValueError("A group admin already uses this username.")
            MasterAdminService().create(username, password)
        except (OSError, ValueError) as exc:
            self.admin_management_error = str(exc)
            return
        self.new_master_admin_username = ""
        self.new_master_admin_password = ""
        self.new_master_admin_confirm_password = ""
        self.show_new_master_admin_password = False
        self.show_new_master_admin_confirm_password = False
        self.load_admin_accounts()
        self.admin_management_message = "Master Admin account was created."

    def open_edit_master_admin_dialog(self):
        if not self._is_developer_authenticated():
            return
        username = self.master_admin.get("username", "")
        if not username:
            self.admin_management_error = "Create the Master Admin account first."
            return
        self.edit_master_admin_username = username
        self.admin_management_error = ""
        self.admin_management_message = ""
        self.show_edit_master_admin_dialog = True

    def close_edit_master_admin_dialog(self):
        self.show_edit_master_admin_dialog = False
        self.edit_master_admin_username = ""

    def set_show_edit_master_admin_dialog(self, is_open: bool):
        self.show_edit_master_admin_dialog = is_open
        if not is_open:
            self.close_edit_master_admin_dialog()

    def set_edit_master_admin_username(self, value: str):
        self.edit_master_admin_username = value
        self.admin_management_error = ""

    def save_master_admin_username(self):
        if not self._is_developer_authenticated():
            return
        old_username = self.master_admin.get("username", "")
        username = self.edit_master_admin_username.strip()
        if not username:
            self.admin_management_error = "Username is required."
            return
        try:
            if any(
                row["username"].casefold() == username.casefold()
                for row in GroupAdminService().get_all()
            ):
                raise ValueError("A group admin already uses this username.")
            MasterAdminService().update(old_username, username)
        except (OSError, ValueError) as exc:
            self.admin_management_error = str(exc)
            return
        self.close_edit_master_admin_dialog()
        self.load_admin_accounts()
        self.admin_management_message = "Master Admin username was updated."

    def open_reset_master_admin_dialog(self):
        if not self._is_developer_authenticated():
            return
        if not self.master_admin.get("username"):
            self.admin_management_error = "Create the Master Admin account first."
            return
        self.reset_master_admin_password = ""
        self.reset_master_admin_confirm_password = ""
        self.show_reset_master_admin_password = False
        self.show_reset_master_admin_confirm_password = False
        self.admin_management_error = ""
        self.admin_management_message = ""
        self.show_reset_master_admin_dialog = True

    def close_reset_master_admin_dialog(self):
        self.show_reset_master_admin_dialog = False
        self.reset_master_admin_password = ""
        self.reset_master_admin_confirm_password = ""
        self.show_reset_master_admin_password = False
        self.show_reset_master_admin_confirm_password = False

    def set_show_reset_master_admin_dialog(self, is_open: bool):
        self.show_reset_master_admin_dialog = is_open
        if not is_open:
            self.close_reset_master_admin_dialog()

    def set_reset_master_admin_password(self, value: str):
        self.reset_master_admin_password = value
        self.admin_management_error = ""

    def set_reset_master_admin_confirm_password(self, value: str):
        self.reset_master_admin_confirm_password = value
        self.admin_management_error = ""

    def toggle_reset_master_admin_password(self):
        self.show_reset_master_admin_password = (
            not self.show_reset_master_admin_password
        )

    def toggle_reset_master_admin_confirm_password(self):
        self.show_reset_master_admin_confirm_password = (
            not self.show_reset_master_admin_confirm_password
        )

    def reset_master_admin_password_now(self):
        if not self._is_developer_authenticated():
            return
        password = self.reset_master_admin_password.strip()
        confirm_password = self.reset_master_admin_confirm_password.strip()
        if not password or not confirm_password:
            self.admin_management_error = "Both password fields are required."
            return
        if password != confirm_password:
            self.admin_management_error = "Passwords do not match."
            return
        username = self.master_admin.get("username", "")
        try:
            MasterAdminService().update(username, username, password)
        except (OSError, ValueError) as exc:
            self.admin_management_error = str(exc)
            return
        self.close_reset_master_admin_dialog()
        self.admin_management_message = "Master Admin password was reset."

    def logout(self):
        self.is_authenticated = False
        self.login_error = ""
        self.show_password = False
        self.active_section = "overview"
        self.master_admin = {"username": ""}
        self.admin_management_error = ""
        self.admin_management_message = ""
        self._clear_admin_management_forms()


def login_page() -> rx.Component:
    return rx.center(
        rx.box(
            rx.vstack(
                rx.image(
                    src="/tvs-logo.png",
                    alt="TVS Motor Company",
                    width="260px",
                    height="auto",
                    object_fit="contain",
                ),
                rx.box(
                    width="44px",
                    height="4px",
                    background="#e34332",
                    border_radius="full",
                ),
                rx.text(
                    "BACKEND DEVELOPER CONSOLE",
                    color="#24427f",
                    font_size="13px",
                    font_weight="700",
                    letter_spacing="0.12em",
                ),
                rx.heading("Secure sign in", size="6", color="#17233c"),
                rx.text(
                    "Authorized backend developers only",
                    color="#64748b",
                    font_size="15px",
                ),
                rx.form(
                    rx.vstack(
                        rx.text("Username", color="#17233c", font_weight="600"),
                        rx.input(
                            name="username",
                            placeholder="Enter your username",
                            required=True,
                            width="100%",
                        ),
                        rx.text("Password", color="#17233c", font_weight="600"),
                        rx.hstack(
                            rx.input(
                                name="password",
                                placeholder="Enter your password",
                                type=rx.cond(
                                    State.show_password, "text", "password"
                                ),
                                required=True,
                                width="100%",
                                flex="1",
                            ),
                            rx.icon_button(
                                rx.cond(
                                    State.show_password,
                                    rx.icon("eye_off"),
                                    rx.icon("eye"),
                                ),
                                type="button",
                                on_click=State.toggle_password,
                                variant="ghost",
                                color="#24427f",
                            ),
                            width="100%",
                            align="center",
                        ),
                        rx.text(State.login_error, color="#c62828", font_size="14px"),
                        rx.button(
                            "Sign In",
                            type="submit",
                            width="100%",
                            background="#24427f",
                            color="white",
                            _hover={"background": "#193465"},
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    on_submit=State.login,
                    reset_on_submit=False,
                    width="100%",
                ),
                rx.text(
                    "Internal access • Do not share your credentials",
                    color="#7b8798",
                    font_size="12px",
                    text_align="center",
                ),
                spacing="4",
                align="center",
                width="100%",
            ),
            width="100%",
            max_width="440px",
            padding="40px",
            background="white",
            border="1px solid #e2e8f0",
            border_radius="20px",
            box_shadow="0 20px 60px rgba(23, 35, 60, 0.10)",
        ),
        min_height="100vh",
        width="100%",
        padding="24px",
        background="#f3f6fb",
    )


def nav_item(label: str, section: str) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.text(label, white_space="nowrap", flex="1"),
            rx.text("›", font_size="20px"),
            width="100%",
            align="center",
            justify="between",
            wrap="nowrap",
        ),
        on_click=State.navigate(section),
        width="100%",
        color=rx.cond(State.active_section == section, "white", "#24427f"),
        background=rx.cond(State.active_section == section, "#24427f", "white"),
        border="1px solid #e2e8f0",
        justify="start",
        _hover={"background": "#edf2fa"},
    )


def stat_card(label: str, value: str, detail: str, accent: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(label, color="#64748b", font_size="14px"),
            rx.heading(value, size="6", color="#17233c"),
            rx.text(detail, color=accent, font_size="13px", font_weight="600"),
            align="start",
            spacing="2",
        ),
        width="100%",
        padding="20px",
        background="white",
        border="1px solid #e2e8f0",
        border_left=f"4px solid {accent}",
        border_radius="12px",
        box_shadow="0 4px 14px rgba(23, 35, 60, 0.04)",
    )


def module_card(
    title: str, description: str, button_label: str, section: str
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(title, size="5", color="#17233c"),
            rx.text(description, color="#64748b"),
            rx.button(
                button_label,
                on_click=State.navigate(section),
                background="#24427f",
                color="white",
                _hover={"background": "#193465"},
            ),
            align="start",
            spacing="4",
        ),
        width="100%",
        padding="24px",
        background="white",
        border="1px solid #e2e8f0",
        border_radius="14px",
        box_shadow="0 4px 14px rgba(23, 35, 60, 0.04)",
    )


def password_field(value, on_change, show, on_toggle, placeholder: str) -> rx.Component:
    return rx.input(
        rx.input.slot(
            rx.icon_button(
                rx.cond(
                    show,
                    rx.icon("eye-off", size=16),
                    rx.icon("eye", size=16),
                ),
                type="button",
                variant="ghost",
                color="#64748b",
                on_click=on_toggle,
                tab_index=-1,
                aria_label="Toggle password visibility",
            ),
            side="right",
        ),
        value=value,
        on_change=on_change,
        type=rx.cond(show, "text", "password"),
        placeholder=placeholder,
        width="100%",
    )


def overview_page() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.heading("System Overview", size="7", color="#17233c"),
            rx.text(
                "Manage administrator access and the application's data store.",
                color="#64748b",
            ),
            align="start",
            spacing="2",
        ),
        rx.grid(
            stat_card("Administrator Access", "Admin Management", "Backend controlled", "#24427f"),
            stat_card("Master Admin", "Protected", "Credentials managed here", "#e34332"),
            stat_card("Database", "Configuration", "Choose a storage option", "#24427f"),
            width="100%",
            columns="3",
            spacing="4",
        ),
        rx.heading("Core Management", size="5", color="#17233c"),
        rx.grid(
            module_card(
                "Admin Management",
                "Manage the Master Admin account.",
                "Open Admin Management",
                "admins",
            ),
            module_card(
                "DB Management",
                "Choose folder-based storage, MySQL, or an API data source.",
                "Open DB Management",
                "database",
            ),
            width="100%",
            columns="2",
            spacing="4",
        ),
        align="start",
        width="100%",
        spacing="5",
    )


def master_admin_creation_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Create Master Admin", size="5", color="#17233c"),
            rx.text(
                "Only the authenticated backend developer can create the Master Admin account.",
                color="#64748b",
                font_size="14px",
            ),
            rx.text("Username", color="#17233c", font_weight="600"),
            rx.input(
                value=State.new_master_admin_username,
                on_change=State.set_new_master_admin_username,
                placeholder="Enter username",
                width="100%",
            ),
            rx.text("Password", color="#17233c", font_weight="600"),
            password_field(
                State.new_master_admin_password,
                State.set_new_master_admin_password,
                State.show_new_master_admin_password,
                State.toggle_new_master_admin_password,
                "Set password",
            ),
            rx.text("Confirm Password", color="#17233c", font_weight="600"),
            password_field(
                State.new_master_admin_confirm_password,
                State.set_new_master_admin_confirm_password,
                State.show_new_master_admin_confirm_password,
                State.toggle_new_master_admin_confirm_password,
                "Confirm password",
            ),
            rx.button(
                "Create Master Admin",
                on_click=State.create_master_admin,
                background="#24427f",
                color="white",
                _hover={"background": "#193465"},
                align_self="end",
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        width="100%",
        max_width="680px",
        padding="22px",
        background="white",
        border="1px solid #e2e8f0",
        border_left="4px solid #e34332",
        border_radius="12px",
    )


def master_admin_edit_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Edit Master Admin", size="5", color="#17233c"),
                rx.text(
                    "Update the Master Admin username.",
                    color="#64748b",
                    font_size="14px",
                ),
                rx.text("Username", color="#17233c", font_weight="600"),
                rx.input(
                    value=State.edit_master_admin_username,
                    on_change=State.set_edit_master_admin_username,
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=State.close_edit_master_admin_dialog,
                        variant="outline",
                        color="#24427f",
                    ),
                    rx.button(
                        "Save Changes",
                        on_click=State.save_master_admin_username,
                        background="#24427f",
                        color="white",
                    ),
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
                align="start",
            ),
            max_width="440px",
        ),
        open=State.show_edit_master_admin_dialog,
        on_open_change=State.set_show_edit_master_admin_dialog,
    )


def master_admin_reset_password_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Reset Master Admin Password", size="5", color="#17233c"),
                rx.text(
                    "The stored password is never shown.",
                    color="#64748b",
                    font_size="14px",
                ),
                rx.text("New Password", color="#17233c", font_weight="600"),
                password_field(
                    State.reset_master_admin_password,
                    State.set_reset_master_admin_password,
                    State.show_reset_master_admin_password,
                    State.toggle_reset_master_admin_password,
                    "Enter new password",
                ),
                rx.text("Confirm New Password", color="#17233c", font_weight="600"),
                password_field(
                    State.reset_master_admin_confirm_password,
                    State.set_reset_master_admin_confirm_password,
                    State.show_reset_master_admin_confirm_password,
                    State.toggle_reset_master_admin_confirm_password,
                    "Confirm new password",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=State.close_reset_master_admin_dialog,
                        variant="outline",
                        color="#24427f",
                    ),
                    rx.button(
                        "Reset Password",
                        on_click=State.reset_master_admin_password_now,
                        background="#24427f",
                        color="white",
                    ),
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
                align="start",
            ),
            max_width="440px",
        ),
        open=State.show_reset_master_admin_dialog,
        on_open_change=State.set_show_reset_master_admin_dialog,
    )


def admin_management_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Admin Management", size="7", color="#17233c"),
        rx.text(
            "Manage the Master Admin account.",
            color="#64748b",
        ),
        rx.cond(
            State.admin_management_error != "",
            rx.box(
                rx.text(State.admin_management_error, color="#b42318", font_size="14px"),
                background="#fef3f2",
                border="1px solid #fecdca",
                border_radius="8px",
                padding="12px 16px",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.admin_management_message != "",
            rx.box(
                rx.text(State.admin_management_message, color="#027a48", font_size="14px"),
                background="#ecfdf3",
                border="1px solid #abefc6",
                border_radius="8px",
                padding="12px 16px",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.master_admin["username"] == "",
            master_admin_creation_form(),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Master Admin", size="5", color="#17233c"),
                        rx.badge("Protected", color_scheme="red", variant="soft"),
                        rx.spacer(),
                        rx.button(
                            "Edit Username",
                            on_click=State.open_edit_master_admin_dialog,
                            variant="outline",
                            color="#24427f",
                        ),
                        rx.button(
                            "Reset Password",
                            on_click=State.open_reset_master_admin_dialog,
                            variant="outline",
                            color="#24427f",
                        ),
                        spacing="3",
                        align="center",
                        width="100%",
                    ),
                    rx.text(
                        State.master_admin["username"],
                        color="#17233c",
                        font_weight="600",
                    ),
                    spacing="3",
                    align="start",
                    width="100%",
                ),
                width="100%",
                padding="22px",
                background="white",
                border="1px solid #e2e8f0",
                border_left="4px solid #e34332",
                border_radius="12px",
            ),
        ),
        master_admin_edit_dialog(),
        master_admin_reset_password_dialog(),
        align="start",
        width="100%",
        spacing="5",
    )


def database_alerts() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.icon("info", size=18, color="#175CD3"),
                rx.text(
                    State.active_storage_status,
                    color="#1849A9",
                    font_size="14px",
                ),
                align="center",
                spacing="3",
            ),
            background="#EFF8FF",
            border="1px solid #B2DDFF",
            border_radius="8px",
            padding="12px 16px",
            width="100%",
        ),
        rx.cond(
            State.database_error != "",
            rx.box(
                rx.text(State.database_error, color="#b42318", font_size="14px"),
                background="#fef3f2",
                border="1px solid #fecdca",
                border_radius="8px",
                padding="12px 16px",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.database_message != "",
            rx.box(
                rx.text(State.database_message, color="#027a48", font_size="14px"),
                background="#ecfdf3",
                border="1px solid #abefc6",
                border_radius="8px",
                padding="12px 16px",
                width="100%",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="3",
    )


def database_input(label: str, value, on_change, placeholder: str = "", input_type: str = "text") -> rx.Component:
    return rx.vstack(
        rx.text(label, color="#17233c", font_size="14px", font_weight="600"),
        rx.input(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            type=input_type,
            width="100%",
            background="white",
            border="1px solid #cbd5e1",
            border_radius="8px",
            padding="10px 12px",
        ),
        spacing="2",
        width="100%",
        align="start",
    )


def database_form_actions(
    test_handler,
    save_handler,
    cancel_handler,
    test_label: str,
    save_label: str = "Save Pending Configuration",
) -> rx.Component:
    return rx.hstack(
        rx.spacer(),
        rx.button(
            "Cancel",
            on_click=cancel_handler,
            variant="outline",
            color="#24427f",
            border="1px solid #cbd5e1",
            background="white",
        ),
        rx.button(
            test_label,
            on_click=test_handler,
            variant="outline",
            color="#24427f",
            border="1px solid #24427f",
            background="white",
        ),
        rx.button(
            save_label,
            on_click=save_handler,
            background="#24427f",
            color="white",
            _hover={"background": "#193465"},
        ),
        width="100%",
        justify="end",
        spacing="3",
        padding_top="16px",
        border_top="1px solid #e2e8f0",
    )


def folder_browser_entry(entry: dict[str, str]) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.icon("folder", size=16, color="#24427f"),
            rx.text(entry["name"], color="#17233c"),
            align="center",
            spacing="2",
            width="100%",
        ),
        on_click=State.browse_folder_directory(entry["path"]),
        variant="ghost",
        width="100%",
        justify="start",
        _hover={"background": "#f1f5f9"},
    )


def folder_browser_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Browse Server Folders", size="5", color="#17233c"),
                rx.text(
                    "Choose a directory on the application server.",
                    color="#64748b",
                    font_size="14px",
                ),
                rx.text(State.folder_browser_path, color="#24427f", font_size="13px"),
                rx.cond(
                    State.folder_browser_error != "",
                    rx.text(State.folder_browser_error, color="#b42318"),
                    rx.fragment(),
                ),
                rx.button(
                    "Up one folder",
                    on_click=State.browse_folder_parent,
                    variant="outline",
                    disabled=State.folder_browser_parent == "",
                ),
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.folder_browser_entries,
                            folder_browser_entry,
                        ),
                        width="100%",
                        align="stretch",
                        spacing="1",
                    ),
                    max_height="320px",
                    overflow_y="auto",
                    width="100%",
                    border="1px solid #e2e8f0",
                    border_radius="8px",
                    padding="8px",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=State.close_folder_browser,
                        variant="outline",
                        color="#24427f",
                    ),
                    rx.button(
                        "Select This Folder",
                        on_click=State.select_folder_browser_path,
                        background="#24427f",
                        color="white",
                    ),
                    justify="end",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            max_width="600px",
        ),
        open=State.folder_browser_open,
        on_open_change=State.set_folder_browser_open,
    )


def database_overview_page() -> rx.Component:
    return rx.vstack(
        rx.heading("DB Management", size="7", color="#17233c"),
        rx.text(
            "Choose and test a server-side data source configuration.",
            color="#64748b",
        ),
        database_alerts(),
        rx.grid(
            database_option_card(
                "Folder Path",
                "Test, migrate, and activate the app's JSON data folder.",
                "Configure Folder Path",
                "folder",
            ),
            database_option_card(
                "MySQL",
                "Validate a MySQL connection and securely save a pending profile.",
                "Configure MySQL",
                "mysql",
            ),
            database_option_card(
                "API",
                "Validate HTTPS transport and save a pending API profile.",
                "Configure API",
                "api",
            ),
            width="100%",
            columns="3",
            spacing="4",
        ),
        align="start",
        width="100%",
        spacing="4",
    )


def database_option_card(
    title: str, description: str, button_label: str, profile_type: str
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(title, size="5", color="#17233c"),
            rx.text(description, color="#64748b"),
            rx.button(
                button_label,
                on_click=State.open_database_form(profile_type),
                background="#24427f",
                color="white",
                _hover={"background": "#193465"},
            ),
            align="start",
            spacing="4",
        ),
        width="100%",
        padding="24px",
        background="white",
        border="1px solid #e2e8f0",
        border_radius="14px",
        box_shadow="0 4px 14px rgba(23, 35, 60, 0.04)",
    )


def folder_configuration_page() -> rx.Component:
    return rx.vstack(
        rx.heading("DB Management", size="7", color="#17233c"),
        rx.button(
            "‹  Back to DB Management",
            on_click=State.back_to_database_management,
            variant="ghost",
            color="#24427f",
        ),
        database_alerts(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("folder", size=26, color="#24427f"),
                    rx.vstack(
                        rx.heading("Configure Folder Path", size="5", color="#17233c"),
                        rx.text(
                            "Move the active JSON data location safely. Existing source files are kept in place.",
                            color="#64748b",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    align="center",
                    spacing="4",
                    width="100%",
                ),
                rx.text("Data folder path *", color="#17233c", font_weight="600"),
                rx.hstack(
                    rx.input(
                        value=State.folder_path,
                        on_change=State.set_folder_path,
                        placeholder="Absolute server path",
                        width="100%",
                        height="54px",
                        font_size="16px",
                        background="white",
                        border="1px solid #cbd5e1",
                        border_radius="8px",
                        padding="12px 14px",
                    ),
                    rx.button(
                        rx.icon("folder-open", size=16),
                        "Browse",
                        on_click=State.open_folder_browser,
                        background="#24427f",
                        color="white",
                        _hover={"background": "#193465"},
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                ),
                rx.text(
                    "On local Windows, Browse opens the native folder picker. If unavailable, use the in-app server-folder browser.",
                    color="#64748b",
                    font_size="13px",
                ),
                rx.hstack(
                    rx.text("Storage Status", color="#17233c", font_weight="700"),
                    rx.text(State.active_storage_status, color="#175CD3", font_size="13px"),
                    spacing="3",
                    align="center",
                    width="100%",
                    padding_top="12px",
                ),
                rx.text(
                    State.database_test_status,
                    color="#64748b",
                    font_size="14px",
                ),
                database_form_actions(
                    State.test_folder_access,
                    State.save_folder_configuration,
                    State.back_to_database_management,
                    "Test Folder Access",
                    "Save and Use",
                ),
                width="100%",
                align="start",
                spacing="4",
            ),
            width="100%",
            padding="28px",
            background="white",
            border="1px solid #e2e8f0",
            border_radius="14px",
            box_shadow="0 4px 14px rgba(23, 35, 60, 0.04)",
        ),
        folder_browser_dialog(),
        align="start",
        width="100%",
        spacing="4",
    )


def mysql_configuration_page() -> rx.Component:
    return rx.vstack(
        rx.heading("DB Management", size="7", color="#17233c"),
        rx.button(
            "‹  Back to DB Management",
            on_click=State.back_to_database_management,
            variant="ghost",
            color="#24427f",
        ),
        database_alerts(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Configure MySQL Database", size="5", color="#17233c"),
                        rx.text(
                            "Validate and save MySQL connection details for review.",
                            color="#64748b",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.text(
                        "Credentials are encrypted and never shown after saving.",
                        color="#175CD3",
                        font_size="13px",
                    ),
                    align="center",
                    width="100%",
                ),
                rx.grid(
                    database_input("Host *", State.mysql_host, State.set_mysql_host, "e.g. localhost or db.example.com"),
                    database_input("Port *", State.mysql_port, State.set_mysql_port, "3306"),
                    database_input("Database Name *", State.mysql_database, State.set_mysql_database, "e.g. myapp_db"),
                    rx.vstack(
                        database_input("Username *", State.mysql_username, State.set_mysql_username, "Leave blank to reuse the saved username"),
                        rx.cond(
                            State.mysql_credentials_configured,
                            rx.text(
                                "Username and password are saved securely.",
                                color="#64748b",
                                font_size="12px",
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Password *", color="#17233c", font_size="14px", font_weight="600"),
                        password_field(
                            State.mysql_password,
                            State.set_mysql_password,
                            State.show_mysql_password,
                            State.toggle_mysql_password,
                            "Enter password or leave blank to reuse the saved secret",
                        ),
                        rx.cond(
                            State.mysql_credentials_configured,
                            rx.text("A password is saved securely.", color="#64748b", font_size="12px"),
                            rx.fragment(),
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("SSL Mode", color="#17233c", font_size="14px", font_weight="600"),
                        rx.select(
                            ["DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"],
                            value=State.mysql_ssl_mode,
                            on_change=State.set_mysql_ssl_mode,
                            width="100%",
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=18, color="#64748b"),
                        rx.vstack(
                            rx.text("Connection Status", color="#64748b", font_size="13px"),
                            rx.text(State.database_test_status, color="#344054", font_weight="600"),
                            spacing="1",
                            align="start",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    background="#f8fafc",
                    border_radius="8px",
                    padding="14px",
                    width="100%",
                ),
                database_form_actions(
                    State.test_mysql_connection,
                    State.save_mysql_configuration,
                    State.back_to_database_management,
                    "Test Connection",
                ),
                width="100%",
                align="start",
                spacing="4",
            ),
            width="100%",
            padding="28px",
            background="white",
            border="1px solid #e2e8f0",
            border_radius="14px",
        ),
        align="start",
        width="100%",
        spacing="4",
    )


def api_credential_fields() -> rx.Component:
    return rx.cond(
        State.api_auth_type == "API Key",
        rx.vstack(
            rx.text("API Key *", color="#17233c", font_size="14px", font_weight="600"),
            password_field(
                State.api_key,
                State.set_api_key,
                State.show_api_credential,
                State.toggle_api_credential_visibility,
                "Enter API key",
            ),
            rx.cond(
                State.api_credentials_configured,
                rx.text("Leave blank to reuse the saved credential.", color="#64748b", font_size="12px"),
                rx.fragment(),
            ),
            width="100%",
            spacing="2",
            align="start",
        ),
        rx.cond(
            State.api_auth_type == "Bearer Token",
            rx.vstack(
                rx.text("Bearer Token *", color="#17233c", font_size="14px", font_weight="600"),
                password_field(
                    State.api_token,
                    State.set_api_token,
                    State.show_api_credential,
                    State.toggle_api_credential_visibility,
                    "Enter bearer token",
                ),
                rx.cond(
                    State.api_credentials_configured,
                    rx.text("Leave blank to reuse the saved credential.", color="#64748b", font_size="12px"),
                    rx.fragment(),
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
            rx.cond(
                State.api_auth_type == "Basic Auth",
                rx.vstack(
                    database_input("Username *", State.api_username, State.set_api_username, "API username"),
                    rx.text("Password *", color="#17233c", font_size="14px", font_weight="600"),
                    password_field(
                        State.api_password,
                        State.set_api_password,
                        State.show_api_credential,
                        State.toggle_api_credential_visibility,
                        "Enter API password",
                    ),
                    rx.cond(
                        State.api_credentials_configured,
                        rx.text(
                            "Leave blank to reuse the saved credentials.",
                            color="#64748b",
                            font_size="12px",
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="2",
                    align="start",
                ),
                rx.text("No credentials are required.", color="#64748b"),
            ),
        ),
    )


def api_configuration_page() -> rx.Component:
    return rx.vstack(
        rx.heading("DB Management", size="7", color="#17233c"),
        rx.button(
            "‹  Back to DB Management",
            on_click=State.back_to_database_management,
            variant="ghost",
            color="#24427f",
        ),
        database_alerts(),
        rx.box(
            rx.vstack(
                rx.heading("Configure API Data Source", size="5", color="#17233c"),
                rx.text(
                    "Validate HTTPS transport and save a pending API profile.",
                    color="#64748b",
                ),
                rx.text(
                    "Credentials are encrypted. API authentication cannot be tested without an API contract.",
                    color="#175CD3",
                    font_size="13px",
                ),
                rx.grid(
                    database_input("Service Name *", State.api_service_name, State.set_api_service_name, "Vehicle Data Service"),
                    database_input("Base URL *", State.api_base_url, State.set_api_base_url, "https://api.example.com"),
                    database_input("API Version *", State.api_version, State.set_api_version, "v1"),
                    rx.vstack(
                        rx.text("Authentication Type *", color="#17233c", font_size="14px", font_weight="600"),
                        rx.select(
                            ["API Key", "Bearer Token", "Basic Auth", "None"],
                            value=State.api_auth_type,
                            on_change=State.set_api_auth_type,
                            width="100%",
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    api_credential_fields(),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("CA Certificate (Optional)", color="#17233c", font_size="14px", font_weight="600"),
                    rx.upload(
                        rx.hstack(
                            rx.icon("cloud-upload", size=20, color="#175CD3"),
                            rx.vstack(
                                rx.text("Upload a CA certificate", color="#175CD3", font_weight="600"),
                                rx.text("Drop a .crt, .cer, or .pem file, or click to browse.", color="#64748b", font_size="13px"),
                                align="start",
                                spacing="1",
                            ),
                            align="center",
                            spacing="3",
                            width="100%",
                            padding="14px",
                            border="1px dashed #cbd5e1",
                            border_radius="8px",
                        ),
                        id="database_ca_certificate_uploader",
                        accept={
                            "application/x-x509-ca-cert": [".pem", ".crt", ".cer"],
                            "application/pkix-cert": [".cer"],
                        },
                        max_files=1,
                        border="none",
                        padding="0",
                        width="100%",
                        on_drop=State.handle_ca_certificate_upload(
                            rx.upload_files(upload_id="database_ca_certificate_uploader")
                        ),
                    ),
                    rx.cond(
                        State.api_ca_certificate_path != "",
                        rx.text("CA certificate is available on the server.", color="#64748b", font_size="12px"),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="2",
                    align="start",
                ),
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=18, color="#64748b"),
                        rx.vstack(
                            rx.text("Connection Status", color="#64748b", font_size="13px"),
                            rx.text(State.database_test_status, color="#344054", font_weight="600"),
                            spacing="1",
                            align="start",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    background="#f8fafc",
                    border_radius="8px",
                    padding="14px",
                    width="100%",
                ),
                database_form_actions(
                    State.test_api_connection,
                    State.save_api_configuration,
                    State.back_to_database_management,
                    "Test Connection",
                ),
                width="100%",
                align="start",
                spacing="4",
            ),
            width="100%",
            padding="28px",
            background="white",
            border="1px solid #e2e8f0",
            border_radius="14px",
        ),
        align="start",
        width="100%",
        spacing="4",
    )


def database_management_page() -> rx.Component:
    return rx.cond(
        State.database_view == "folder",
        folder_configuration_page(),
        rx.cond(
            State.database_view == "mysql",
            mysql_configuration_page(),
            rx.cond(
                State.database_view == "api",
                api_configuration_page(),
                database_overview_page(),
            ),
        ),
    )


def current_section() -> rx.Component:
    return rx.cond(
        State.active_section == "admins",
        admin_management_page(),
        rx.cond(
            State.active_section == "database",
            database_management_page(),
            overview_page(),
        ),
    )


def console_home() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.image(
                src="/tvs-logo.png",
                alt="TVS Motor Company",
                width="170px",
                height="auto",
                object_fit="contain",
            ),
            rx.text(
                "DEVELOPER CONSOLE",
                color="#24427f",
                font_size="12px",
                font_weight="700",
                letter_spacing="0.1em",
            ),
            rx.divider(),
            nav_item("Overview", "overview"),
            nav_item("Admin Management", "admins"),
            nav_item("DB Management", "database"),
            rx.spacer(),
            rx.button(
                "Sign Out",
                on_click=State.logout,
                width="100%",
                background="white",
                color="#b42318",
                border="1px solid #f1c7c3",
            ),
            align="start",
            width="260px",
            min_height="100vh",
            padding="24px 18px",
            background="white",
            border_right="1px solid #e2e8f0",
        ),
        rx.vstack(
            rx.hstack(
                rx.heading("Backend Developer Console", size="5", color="#17233c"),
                rx.spacer(),
                rx.text("Internal access", color="#64748b", font_size="14px"),
                width="100%",
            ),
            rx.divider(),
            current_section(),
            align="start",
            width="100%",
            padding="30px",
            spacing="5",
        ),
        align="start",
        width="100%",
        min_height="100vh",
        background="#f3f6fb",
        spacing="0",
    )


def index() -> rx.Component:
    return rx.cond(State.is_authenticated, console_home(), login_page())


app = rx.App(theme=rx.theme(appearance="light", accent_color="blue"))
app.add_page(index)
