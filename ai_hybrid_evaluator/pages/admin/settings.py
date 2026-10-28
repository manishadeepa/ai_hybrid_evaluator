import os
import reflex as rx
from datetime import datetime
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY
from backend.services.ai_connection_service import AIConnectionService


# ─────────────────────────────────────────────────────────────
# Settings state
# ─────────────────────────────────────────────────────────────

class SettingsState(rx.State):
    # ── View mode: "select" (initial) | "new" | "current" ─────
    active_view: str = "select"
    show_selection_dialog: bool = False

    # ── AI Connection form fields ─────────────────────────────
    ai_conn_name: str = ""
    ai_conn_endpoint: str = ""
    ai_conn_model: str = ""
    ai_conn_api_version: str = ""
    ai_conn_cert: str = ""
    ai_conn_api_key: str = ""
    ai_conn_show_key: bool = False   # toggle API key visibility in the form

    # ── Saved AI Connection (populated or default active) ────
    ai_saved_name: str = ""
    ai_saved_connection_id: str = ""
    ai_conn_editing_existing: bool = False
    ai_conn_edit_id: str = ""
    ai_saved_endpoint: str = ""
    ai_saved_model: str = ""
    ai_saved_api_version: str = ""
    ai_saved_cert: str = "Not configured"
    ai_saved_last_tested: str = "Aug 31, 2026, 09:15 AM"
    ai_saved_status: str = "success"        # "success" | "error" | ""
    ai_saved_show_key: bool = False         # toggle masked key in current connection view

    # ── Navigation / Selection methods ────────────────────────
    def set_show_selection_dialog(self, v: bool):
        self.show_selection_dialog = v

    def open_selection_dialog(self):
        self.show_selection_dialog = False
        self.ai_conn_editing_existing = False
        self.ai_conn_edit_id = ""
        self.active_view = "select"

    def choose_create_new(self):
        self.show_selection_dialog = False
        self.active_view = "new"

    def choose_current_connection(self):
        self.show_selection_dialog = False
        self.active_view = "current"

    # ── AI Connection field setters ───────────────────────────
    def set_ai_conn_name(self, v: str): self.ai_conn_name = v
    def set_ai_conn_endpoint(self, v: str): self.ai_conn_endpoint = v
    def set_ai_conn_model(self, v: str): self.ai_conn_model = v
    def set_ai_conn_api_version(self, v: str): self.ai_conn_api_version = v
    def set_ai_conn_cert(self, v: str): self.ai_conn_cert = v
    def set_ai_conn_api_key(self, value: str): self.ai_conn_api_key = value
    def toggle_ai_conn_show_key(self): self.ai_conn_show_key = not self.ai_conn_show_key
    def toggle_ai_saved_show_key(self): self.ai_saved_show_key = not self.ai_saved_show_key

    # ── AI Connection actions ─────────────────────────────────

    def load_active_connection(self):
        service = AIConnectionService()
        connection = service.get_active_public()

        if not connection:
            return

        self.ai_saved_connection_id = connection.get("connection_id", "")
        self.ai_saved_name = connection.get("name", "")
        self.ai_saved_endpoint = connection.get("endpoint", "") or "OpenAI"
        self.ai_saved_model = connection.get("model", "") or "Not configured"
        self.ai_saved_api_version = connection.get("api_version", "") or "Not applicable"
        self.ai_saved_cert = connection.get("cert_path", "") or "Not configured"
        self.ai_saved_last_tested = connection.get("last_tested_at", "")
        self.ai_saved_status = connection.get("status", "")

    def _connection_form(self):
        return {
            "name": self.ai_conn_name,
            "endpoint": self.ai_conn_endpoint,
            "model": self.ai_conn_model,
            "api_version": self.ai_conn_api_version,
            "cert_path": self.ai_conn_cert,
            "api_key": self.ai_conn_api_key,
        }

    def ai_test_connection(self):
        try:
            service = AIConnectionService()
            form = self._connection_form()
            # If in Existing AI Connection view and form has not been filled, test active connection
            if not form.get("name") and self.ai_saved_name:
                client, model, http_client = service.get_active_client()
                try:
                    active_rec = service.repository.get_active()
                    if active_rec and active_rec.get("provider") == "azure":
                        client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": "Reply OK."}],
                            max_tokens=1,
                        )
                    else:
                        client.models.list()
                finally:
                    http_client.close()
                from datetime import datetime, timezone
                self.ai_saved_last_tested = datetime.now(timezone.utc).isoformat()
                self.ai_saved_status = "success"
                return rx.toast.success("Connection test succeeded.")

            result = service.test_connection(
                form,
                connection_id=(self.ai_conn_edit_id if self.ai_conn_editing_existing else None),
            )
            self.ai_saved_last_tested = result["last_tested_at"]
            self.ai_saved_status = "success"
            return rx.toast.success("Connection test succeeded.")
        except Exception as exc:
            self.ai_saved_status = "error"
            return rx.toast.error(str(exc))

    def ai_save_and_use(self):
        form = self._connection_form()
        editing_existing = self.ai_conn_editing_existing and bool(self.ai_conn_edit_id)
        if not form.get("name") and self.ai_saved_name and not editing_existing:
            return rx.toast.success("Existing connection is already saved and active.")
        try:
            record = AIConnectionService().save_and_activate(
                form,
                connection_id=(self.ai_conn_edit_id if editing_existing else None),
            )
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

        self.ai_saved_connection_id = record["connection_id"]
        self.ai_saved_name = record["name"]
        self.ai_saved_endpoint = record["endpoint"] or "OpenAI"
        self.ai_saved_model = record["model"] or "Not configured"
        self.ai_saved_api_version = (
            record["api_version"] or "Not applicable"
        )
        self.ai_saved_cert = record["cert_path"] or "Not configured"
        self.ai_saved_last_tested = record["last_tested_at"]
        self.ai_saved_status = "success"

        self.ai_conn_api_key = ""
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_show_key = False
        self.ai_conn_editing_existing = False
        self.ai_conn_edit_id = ""
        self.active_view = "current"
        self.show_selection_dialog = False

        return rx.toast.success(
            "Connection tested, saved, and activated."
        )

    def ai_cancel_form(self):
        """Discard the form and return to the prior connection view."""
        returning_to_existing = self.ai_conn_editing_existing
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_api_key = ""
        self.ai_conn_show_key = False
        self.ai_conn_editing_existing = False
        self.ai_conn_edit_id = ""
        self.active_view = "current" if returning_to_existing else "select"
        self.show_selection_dialog = False

    def ai_replace_connection(self):
        """Transition from current connection to the new connection form."""
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_api_key = ""
        self.ai_conn_show_key = False
        self.ai_conn_editing_existing = False
        self.ai_conn_edit_id = ""
        self.active_view = "new"
        self.show_selection_dialog = False

    def ai_edit_connection(self):
        """Unlock the active connection fields for editing."""
        if not self.ai_saved_connection_id:
            self.load_active_connection()
        if not self.ai_saved_connection_id:
            return rx.toast.error("No saved AI connection is available to edit.")
        self.ai_conn_editing_existing = True
        self.ai_conn_edit_id = self.ai_saved_connection_id
        self.ai_conn_name = self.ai_saved_name
        self.ai_conn_endpoint = self.ai_saved_endpoint if self.ai_saved_endpoint != "OpenAI" else ""
        self.ai_conn_model = self.ai_saved_model if self.ai_saved_model != "Not configured" else ""
        self.ai_conn_api_version = self.ai_saved_api_version if self.ai_saved_api_version != "Not applicable" else ""
        self.ai_conn_cert = self.ai_saved_cert if self.ai_saved_cert != "Not configured" else ""
        try:
            self.ai_conn_api_key = AIConnectionService().get_decrypted_api_key(
                self.ai_saved_connection_id
            )
        except (ValueError, OSError) as exc:
            self.ai_conn_editing_existing = False
            self.ai_conn_edit_id = ""
            return rx.toast.error(str(exc))
        self.ai_conn_show_key = False
        self.active_view = "current"
        self.show_selection_dialog = False

    # ── Access Control State ──────────────────────────────────
    admin_accounts: list[dict] = []

    # Add Admin Dialog State
    show_add_admin_dialog: bool = False
    new_admin_username: str = ""
    new_admin_password: str = ""
    new_admin_confirm_password: str = ""
    show_new_admin_password: bool = False
    show_new_admin_confirm_password: bool = False
    add_admin_error: str = ""

    # Edit Admin Dialog State
    show_edit_admin_dialog: bool = False
    edit_admin_index: int = -1
    edit_admin_username: str = ""
    edit_admin_password: str = ""
    edit_admin_confirm_password: str = ""
    show_edit_admin_password: bool = False
    show_edit_admin_confirm_password: bool = False
    edit_admin_error: str = ""

    # Delete Admin Dialog State
    show_delete_admin_dialog: bool = False
    delete_admin_index: int = -1
    delete_admin_username: str = ""

    # View Admin Dialog State
    show_view_admin_dialog: bool = False
    view_admin_username: str = ""
    view_admin_password: str = ""
    view_admin_show_password: bool = False

    def load_admin_accounts(self):
        """Loads administrator accounts, ensuring Master Admin (Manisha) is authoritative at #1."""
        if self.admin_accounts:
            return

        master_name = "Manisha"
        from ai_hybrid_evaluator.services.mock_api import find_admin_excel_path
        excel_path = find_admin_excel_path()
        other_names = []
        if excel_path and os.path.isfile(excel_path):
            try:
                import pandas as pd
                df = pd.read_excel(excel_path)
                col_map = {str(c).strip().lower(): c for c in df.columns}
                name_col = col_map.get("employeename")
                if name_col:
                    for _, row in df.iterrows():
                        raw_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                        if raw_name:
                            if raw_name.lower() == master_name.lower():
                                master_name = raw_name
                            elif raw_name not in other_names:
                                other_names.append(raw_name)
            except Exception:
                pass

        if not other_names:
            other_names = ["Kannadasan R", "Sudhir", "Vaghee", "Shivani"]

        accounts = [
            {
                "num": "1",
                "username": master_name,
                "role": "Master Admin",
                "status": "Active",
                "is_master": True,
            }
        ]
        for i, name in enumerate(other_names):
            status = "Inactive" if name.lower() == "arun" else "Active"
            accounts.append({
                "num": str(i + 2),
                "username": name,
                "role": "Administrator",
                "status": status,
                "is_master": False,
            })
        self.admin_accounts = accounts

    def on_page_load(self):
        self.load_active_connection()
        self.load_admin_accounts()

    # ── Add Admin Handlers ────────────────────────────────────
    def open_add_admin_dialog(self):
        self.new_admin_username = ""
        self.new_admin_password = ""
        self.new_admin_confirm_password = ""
        self.show_new_admin_password = False
        self.show_new_admin_confirm_password = False
        self.add_admin_error = ""
        self.show_add_admin_dialog = True

    def close_add_admin_dialog(self):
        self.show_add_admin_dialog = False
        self.add_admin_error = ""

    def set_show_add_admin_dialog(self, v: bool):
        self.show_add_admin_dialog = v
        if not v:
            self.add_admin_error = ""

    def toggle_new_admin_password(self):
        self.show_new_admin_password = not self.show_new_admin_password

    def toggle_new_admin_confirm_password(self):
        self.show_new_admin_confirm_password = not self.show_new_admin_confirm_password

    def set_new_admin_username(self, v: str):
        self.new_admin_username = v
        self.add_admin_error = ""

    def set_new_admin_password(self, v: str):
        self.new_admin_password = v
        self.add_admin_error = ""

    def set_new_admin_confirm_password(self, v: str):
        self.new_admin_confirm_password = v
        self.add_admin_error = ""

    def create_admin(self):
        uname = self.new_admin_username.strip()
        pwd = self.new_admin_password.strip()
        cpwd = self.new_admin_confirm_password.strip()

        if not uname:
            self.add_admin_error = "Username is required."
            return
        if not pwd:
            self.add_admin_error = "Password is required."
            return
        if not cpwd:
            self.add_admin_error = "Please confirm your password."
            return
        if pwd != cpwd:
            self.add_admin_error = "Passwords do not match."
            return

        for a in self.admin_accounts:
            if a.get("username", "").strip().lower() == uname.lower():
                self.add_admin_error = "An administrator with this username already exists."
                return

        new_num = str(len(self.admin_accounts) + 1)
        new_account = {
            "num": new_num,
            "username": uname,
            "role": "Administrator",
            "status": "Active",
            "is_master": False,
        }
        self.admin_accounts.append(new_account)
        self.show_add_admin_dialog = False
        return rx.toast.success(f"Administrator '{uname}' created successfully.")

    # ── Edit Admin Handlers ───────────────────────────────────
    def open_edit_admin_dialog(self, index: int):
        if not (0 <= index < len(self.admin_accounts)):
            return
        target = self.admin_accounts[index]
        if target.get("is_master"):
            return rx.toast.error("Master admin cannot be edited.")
        self.edit_admin_index = index
        self.edit_admin_username = target.get("username", "")
        self.edit_admin_password = ""
        self.edit_admin_confirm_password = ""
        self.show_edit_admin_password = False
        self.show_edit_admin_confirm_password = False
        self.edit_admin_error = ""
        self.show_edit_admin_dialog = True

    def close_edit_admin_dialog(self):
        self.show_edit_admin_dialog = False
        self.edit_admin_error = ""

    def set_show_edit_admin_dialog(self, v: bool):
        self.show_edit_admin_dialog = v
        if not v:
            self.edit_admin_error = ""

    def toggle_edit_admin_password(self):
        self.show_edit_admin_password = not self.show_edit_admin_password

    def toggle_edit_admin_confirm_password(self):
        self.show_edit_admin_confirm_password = not self.show_edit_admin_confirm_password

    def set_edit_admin_username(self, v: str):
        self.edit_admin_username = v
        self.edit_admin_error = ""

    def set_edit_admin_password(self, v: str):
        self.edit_admin_password = v
        self.edit_admin_error = ""

    def set_edit_admin_confirm_password(self, v: str):
        self.edit_admin_confirm_password = v
        self.edit_admin_error = ""

    def save_admin_changes(self):
        if not (0 <= self.edit_admin_index < len(self.admin_accounts)):
            return
        uname = self.edit_admin_username.strip()
        pwd = self.edit_admin_password.strip()
        cpwd = self.edit_admin_confirm_password.strip()

        if not uname:
            self.edit_admin_error = "Username is required."
            return

        if pwd or cpwd:
            if pwd != cpwd:
                self.edit_admin_error = "Passwords do not match."
                return

        for i, a in enumerate(self.admin_accounts):
            if i != self.edit_admin_index and a.get("username", "").strip().lower() == uname.lower():
                self.edit_admin_error = "An administrator with this username already exists."
                return

        updated = list(self.admin_accounts)
        updated[self.edit_admin_index]["username"] = uname
        self.admin_accounts = updated
        self.show_edit_admin_dialog = False
        return rx.toast.success(f"Administrator details updated for '{uname}'.")

    # ── Delete Admin Handlers ─────────────────────────────────
    def open_delete_admin_dialog(self, index: int):
        if not (0 <= index < len(self.admin_accounts)):
            return
        target = self.admin_accounts[index]
        if target.get("is_master"):
            return rx.toast.error("Master admin cannot be deleted.")
        self.delete_admin_index = index
        self.delete_admin_username = target.get("username", "")
        self.show_delete_admin_dialog = True

    def close_delete_admin_dialog(self):
        self.show_delete_admin_dialog = False
        self.delete_admin_index = -1
        self.delete_admin_username = ""

    def set_show_delete_admin_dialog(self, v: bool):
        self.show_delete_admin_dialog = v

    def confirm_delete_admin(self):
        if not (0 <= self.delete_admin_index < len(self.admin_accounts)):
            return
        uname = self.delete_admin_username
        updated = [a for i, a in enumerate(self.admin_accounts) if i != self.delete_admin_index]
        for idx, a in enumerate(updated):
            a["num"] = str(idx + 1)
        self.admin_accounts = updated
        self.show_delete_admin_dialog = False
        self.delete_admin_index = -1
        self.delete_admin_username = ""
        return rx.toast.success(f"Administrator '{uname}' deleted.")

    # ── View Admin Handlers ───────────────────────────────────
    def open_view_admin_dialog(self, index: int):
        if not (0 <= index < len(self.admin_accounts)):
            return
        target = self.admin_accounts[index]
        self.view_admin_username = target.get("username", "")
        self.view_admin_password = target.get("password", "")
        self.view_admin_show_password = False
        self.show_view_admin_dialog = True

    def close_view_admin_dialog(self):
        self.show_view_admin_dialog = False
        self.view_admin_show_password = False

    def set_show_view_admin_dialog(self, v: bool):
        self.show_view_admin_dialog = v
        if not v:
            self.view_admin_show_password = False

    def toggle_view_admin_show_password(self):
        self.view_admin_show_password = not self.view_admin_show_password


# ─────────────────────────────────────────────────────────────
# UI Helper components
# ─────────────────────────────────────────────────────────────

def _ai_field_label(text: str, required: bool = False) -> rx.Component:
    """Field label with optional red asterisk."""
    return rx.hstack(
        rx.text(text, font_family=FONT_BODY, size="2",
                weight="medium", color=COLORS["ink"]),
        rx.cond(
            required,
            rx.text(" *", font_family=FONT_BODY, size="2",
                    color="#DC2626", weight="bold"),
            rx.fragment(),
        ),
        spacing="0",
        align_items="center",
    )


def _ai_display_field(label: str, value: rx.Var) -> rx.Component:
    """Read-only labelled display box for the Existing Connection card."""
    return rx.vstack(
        rx.text(label, font_family=FONT_BODY, size="2",
                weight="medium", color=COLORS["ink"]),
        rx.box(
            rx.text(value, font_family=FONT_BODY, size="2", color=COLORS["ink"]),
            background="#F8FAFC",
            border=f"1.5px solid {COLORS['line']}",
            border_radius="8px",
            padding="0.65em 0.9em",
            width="100%",
        ),
        spacing="1",
        width="100%",
        align_items="stretch",
    )


# ─────────────────────────────────────────────────────────────
# Selection Dialog & Initial Card
# ─────────────────────────────────────────────────────────────

def selection_dialog() -> rx.Component:
    """Modal selection dialog shown initially when opening AI Connection Settings."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.box(
                        rx.icon("bot", size=22, color="#4F46E5"),
                        background="#EEF2FF",
                        padding="0.6em",
                        border_radius="10px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.dialog.title(
                            "AI Connection",
                            font_family=FONT_BODY,
                            size="4",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.dialog.description(
                            "Select an option to proceed.",
                            size="2",
                            color=COLORS["slate"],
                            font_family=FONT_BODY,
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Option 1: Create New Connection
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("circle-plus", size=22, color="#4F46E5"),
                            background="#EEF2FF",
                            padding="0.65em",
                            border_radius="8px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text(
                                "Create New Connection",
                                font_family=FONT_BODY,
                                size="3",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Add a new API/AI provider connection for evaluation.",
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.icon("chevron-right", size=18, color=COLORS["slate"]),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    on_click=SettingsState.choose_create_new,
                    padding="1.1em 1.2em",
                    border=f"1.5px solid {COLORS['line']}",
                    border_radius="12px",
                    cursor="pointer",
                    _hover={
                        "border_color": "#4F46E5",
                        "background": "#F5F3FF",
                    },
                    transition="all 0.15s ease",
                    width="100%",
                ),

                # Option 2: Existing AI Connection
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("circle-check", size=22, color="#16A34A"),
                            background="#DCFCE7",
                            padding="0.65em",
                            border_radius="8px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text(
                                "Existing AI Connection",
                                font_family=FONT_BODY,
                                size="3",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "View and manage your active AI connection.",
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.icon("chevron-right", size=18, color=COLORS["slate"]),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    on_click=SettingsState.choose_current_connection,
                    padding="1.1em 1.2em",
                    border=f"1.5px solid {COLORS['line']}",
                    border_radius="12px",
                    cursor="pointer",
                    _hover={
                        "border_color": "#16A34A",
                        "background": "#F0FDF4",
                    },
                    transition="all 0.15s ease",
                    width="100%",
                ),

                spacing="3",
                width="100%",
                align_items="stretch",
            ),
            max_width="480px",
            border_radius="14px",
            padding="1.6em",
            background="white",
        ),
        open=SettingsState.show_selection_dialog,
        on_open_change=SettingsState.set_show_selection_dialog,
    )


def _selection_view_card() -> rx.Component:
    """Card shown on the page when in selection mode."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("bot", size=20, color="#4F46E5"),
                    background="#EEF2FF",
                    padding="0.7em",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("AI Connection Settings",
                            font_family=FONT_BODY, size="3",
                            weight="bold", color=COLORS["ink"]),
                    rx.text("Select an option below to proceed with AI connection setup.",
                            font_family=FONT_BODY, size="1",
                            color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                padding_bottom="1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
                width="100%",
            ),

            # Option 1
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.icon("circle-plus", size=22, color="#4F46E5"),
                        background="#EEF2FF",
                        padding="0.65em",
                        border_radius="8px",
                    ),
                    rx.vstack(
                        rx.text("Create New Connection", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                        rx.text("Add a new API/AI provider connection for evaluation.", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.icon("chevron-right", size=18, color=COLORS["slate"]),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                on_click=SettingsState.choose_create_new,
                padding="1.1em 1.2em",
                border=f"1.5px solid {COLORS['line']}",
                border_radius="12px",
                cursor="pointer",
                _hover={"border_color": "#4F46E5", "background": "#F5F3FF"},
                transition="all 0.15s ease",
                width="100%",
            ),

            # Option 2
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.icon("circle-check", size=22, color="#16A34A"),
                        background="#DCFCE7",
                        padding="0.65em",
                        border_radius="8px",
                    ),
                    rx.vstack(
                        rx.text("Existing AI Connection", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                        rx.text("View and manage your active AI connection.", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.icon("chevron-right", size=18, color=COLORS["slate"]),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                on_click=SettingsState.choose_current_connection,
                padding="1.1em 1.2em",
                border=f"1.5px solid {COLORS['line']}",
                border_radius="12px",
                cursor="pointer",
                _hover={"border_color": "#16A34A", "background": "#F0FDF4"},
                transition="all 0.15s ease",
                width="100%",
            ),

            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.75em",
        width="100%",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.04)",
    )


# ─────────────────────────────────────────────────────────────
# 1. Create New Connection Card
# ─────────────────────────────────────────────────────────────

def _new_connection_card() -> rx.Component:
    """Form card shown when user chooses Create New Connection."""
    return rx.box(
        rx.vstack(
            # ── Card header ──────────────────────────────────────
            rx.hstack(
                rx.box(
                    rx.icon("plug", size=20, color="#4F46E5"),
                    background="#EEF2FF",
                    padding="0.7em",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("Create New AI Connection",
                            font_family=FONT_BODY, size="3",
                            weight="bold", color=COLORS["ink"]),
                    rx.text("Add a new API/AI provider connection for evaluation.",
                            font_family=FONT_BODY, size="1",
                            color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                spacing="3",
                align_items="center",
                padding_bottom="1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
                width="100%",
            ),

            # ── 1. Connection Name ────────────────────────────────
            rx.vstack(
                _ai_field_label("Connection Name", required=True),
                rx.input(
                    placeholder="Enter a unique connection name",
                    value=SettingsState.ai_conn_name,
                    on_change=SettingsState.set_ai_conn_name,
                    width="100%", size="3",
                    background="white",
                    border=f"1.5px solid {COLORS['line']}",
                    _focus={"border_color": COLORS["primary"],
                            "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                    font_family=FONT_BODY,
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── 2. Endpoint ───────────────────────────────────────
            rx.vstack(
                _ai_field_label("Endpoint", required=True),
                rx.input(
                    placeholder="https://...",
                    value=SettingsState.ai_conn_endpoint,
                    on_change=SettingsState.set_ai_conn_endpoint,
                    width="100%", size="3",
                    background="white",
                    border=f"1.5px solid {COLORS['line']}",
                    _focus={"border_color": COLORS["primary"],
                            "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                    font_family=FONT_BODY,
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── 3. Model / Deployment ─────────────────────────────
            rx.vstack(
                _ai_field_label("Model / Deployment", required=True),
                rx.input(
                    placeholder="Model or deployment name",
                    value=SettingsState.ai_conn_model,
                    on_change=SettingsState.set_ai_conn_model,
                    width="100%", size="3",
                    background="white",
                    border=f"1.5px solid {COLORS['line']}",
                    _focus={"border_color": COLORS["primary"],
                            "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                    font_family=FONT_BODY,
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── 4. API Version ────────────────────────────────────
            rx.vstack(
                _ai_field_label("API Version", required=True),
                rx.input(
                    placeholder="e.g. 2024-02-15-preview",
                    value=SettingsState.ai_conn_api_version,
                    on_change=SettingsState.set_ai_conn_api_version,
                    width="100%", size="3",
                    background="white",
                    border=f"1.5px solid {COLORS['line']}",
                    _focus={"border_color": COLORS["primary"],
                            "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                    font_family=FONT_BODY,
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── 5. CA Certificate + Browse ────────────────────────
            rx.vstack(
                rx.hstack(
                    _ai_field_label("CA Certificate"),
                    rx.icon("info", size=14, color=COLORS["slate"]),
                    spacing="1",
                    align_items="center",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Optional corporate CA certificate bundle",
                        value=SettingsState.ai_conn_cert,
                        on_change=SettingsState.set_ai_conn_cert,
                        flex="1", size="3",
                        background="white",
                        border=f"1.5px solid {COLORS['line']}",
                        _focus={"border_color": COLORS["primary"],
                                "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                        font_family=FONT_BODY,
                    ),
                    rx.button(
                        "Browse...",
                        size="3",
                        variant="outline",
                        color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}",
                        background="white",
                        font_family=FONT_BODY,
                        _hover={"background": COLORS["canvas"]},
                        cursor="pointer",
                        white_space="nowrap",
                    ),
                    spacing="2",
                    width="100%",
                    align_items="center",
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── 6. API Key ────────────────────────────────────────
            rx.vstack(
                _ai_field_label("API Key", required=True),
                rx.hstack(
                    rx.input(
                        placeholder="Enter API key",
                        on_change=SettingsState.set_ai_conn_api_key,
                        type=rx.cond(SettingsState.ai_conn_show_key, "text", "password"),
                        flex="1", size="3",
                        background="white",
                        border=f"1.5px solid {COLORS['line']}",
                        _focus={"border_color": COLORS["primary"],
                                "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                        font_family=FONT_BODY,
                    ),
                    rx.icon_button(
                        rx.cond(
                            SettingsState.ai_conn_show_key,
                            rx.icon("eye-off", size=16),
                            rx.icon("eye", size=16),
                        ),
                        on_click=SettingsState.toggle_ai_conn_show_key,
                        variant="ghost",
                        color=COLORS["slate"],
                        size="3",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                    ),
                    spacing="1",
                    width="100%",
                    align_items="center",
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── Info note ─────────────────────────────────────────
            rx.box(
                rx.hstack(
                    rx.icon("info", size=15, color="#4338CA"),
                    rx.text(
                        "For direct OpenAI, only Connection name and API key are required. "
                        "Endpoint and Model may remain blank. "
                        "The application securely stores the API key.",
                        font_family=FONT_BODY, size="1", color="#4338CA",
                    ),
                    spacing="2",
                    align_items="start",
                ),
                background="#EEF2FF",
                border_radius="8px",
                padding="0.85em 1em",
                width="100%",
            ),

            # ── Action buttons ────────────────────────────────────
            rx.hstack(
                rx.button(
                    rx.icon("radio", size=14),
                    "Test Connection",
                    on_click=SettingsState.ai_test_connection,
                    variant="outline",
                    color=COLORS["ink"],
                    border=f"1.5px solid {COLORS['line']}",
                    background="white",
                    font_family=FONT_BODY,
                    size="2",
                    cursor="pointer",
                    _hover={"background": COLORS["canvas"]},
                ),
                rx.spacer(),
                rx.button(
                    "Cancel",
                    on_click=SettingsState.ai_cancel_form,
                    variant="outline",
                    color=COLORS["slate"],
                    border=f"1.5px solid {COLORS['line']}",
                    background="white",
                    font_family=FONT_BODY,
                    size="2",
                    cursor="pointer",
                    _hover={"background": COLORS["canvas"]},
                ),
                rx.button(
                    "Save and Use",
                    on_click=SettingsState.ai_save_and_use,
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    size="2",
                    _hover={"background": COLORS["primary_hover"]},
                    cursor="pointer",
                ),
                width="100%",
                align_items="center",
                padding_top="0.5em",
            ),

            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.75em",
        width="100%",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.04)",
    )


# ─────────────────────────────────────────────────────────────
# 2. Existing AI Connection Card
# ─────────────────────────────────────────────────────────────

def _current_connection_edit_field(label: str, saved_value, edit_value, setter) -> rx.Component:
    """Render a saved value read-only until Edit unlocks the current card."""
    return rx.cond(
        SettingsState.ai_conn_editing_existing,
        rx.vstack(
            _ai_field_label(label, required=label == "Connection Name"),
            rx.input(
                value=edit_value,
                on_change=setter,
                width="100%", size="3", background="white",
                border=f"1.5px solid {COLORS['line']}",
                _focus={"border_color": COLORS["primary"],
                        "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                font_family=FONT_BODY,
            ),
            spacing="1", width="100%", align_items="stretch",
        ),
        _ai_display_field(label, saved_value),
    )


def _current_connection_api_key() -> rx.Component:
    """Keep the existing secret masked; let admins optionally replace it inline."""
    return rx.cond(
        SettingsState.ai_conn_editing_existing,
        rx.vstack(
            _ai_field_label("API Key"),
            rx.text(
                "The saved API key is loaded in the password field. It remains masked unless you select the eye icon.",
                font_family=FONT_BODY, size="1", color=COLORS["slate"],
            ),
            rx.hstack(
                rx.input(
                    value=SettingsState.ai_conn_api_key,
                    placeholder="Enter API key",
                    on_change=SettingsState.set_ai_conn_api_key,
                    type=rx.cond(SettingsState.ai_conn_show_key, "text", "password"),
                    flex="1", size="3", background="white",
                    border=f"1.5px solid {COLORS['line']}",
                    _focus={"border_color": COLORS["primary"],
                            "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
                    font_family=FONT_BODY,
                ),
                rx.icon_button(
                    rx.cond(SettingsState.ai_conn_show_key,
                            rx.icon("eye-off", size=16), rx.icon("eye", size=16)),
                    on_click=SettingsState.toggle_ai_conn_show_key,
                    variant="ghost", color=COLORS["slate"], size="3", cursor="pointer",
                ),
                spacing="1", width="100%", align_items="center",
            ),
            spacing="1", width="100%", align_items="stretch",
        ),
        rx.vstack(
            rx.text("API Key", font_family=FONT_BODY, size="2",
                    weight="medium", color=COLORS["ink"]),
            rx.hstack(
                rx.box(
                    rx.cond(
                        SettingsState.ai_saved_show_key,
                        rx.text("(Key stored securely — not displayable)",
                                font_family=FONT_BODY, size="2", color=COLORS["slate"],
                                font_style="italic"),
                        rx.text("••••••••••••••••••••••••",
                                font_family=FONT_BODY, size="2", color=COLORS["ink"],
                                letter_spacing="2px"),
                    ),
                    background="#F8FAFC", border=f"1.5px solid {COLORS['line']}",
                    border_radius="8px", padding="0.65em 0.9em", flex="1",
                ),
                rx.icon_button(
                    rx.cond(SettingsState.ai_saved_show_key,
                            rx.icon("eye-off", size=16), rx.icon("eye", size=16)),
                    on_click=SettingsState.toggle_ai_saved_show_key,
                    variant="ghost", color=COLORS["slate"], size="3", cursor="pointer",
                    _hover={"background": COLORS["canvas"]},
                ),
                spacing="1", width="100%", align_items="center",
            ),
            spacing="1", width="100%", align_items="stretch",
        ),
    )


def _current_connection_card() -> rx.Component:
    """Show the existing connection and unlock its fields inline when Edit is clicked."""
    return rx.box(
        rx.vstack(
            # ── Card header ──────────────────────────────────────
            rx.hstack(
                rx.box(
                    rx.icon("circle-check", size=20, color="#16A34A"),
                    background="#DCFCE7",
                    padding="0.7em",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("Existing AI Connection",
                            font_family=FONT_BODY, size="3",
                            weight="bold", color=COLORS["ink"]),
                    rx.text("View and manage your active AI connection.",
                            font_family=FONT_BODY, size="1",
                            color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                spacing="3",
                align_items="center",
                padding_bottom="1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
                width="100%",
            ),

            # ── 1. Connection Name ────────────────────────────────
            _current_connection_edit_field(
                "Connection Name", SettingsState.ai_saved_name,
                SettingsState.ai_conn_name, SettingsState.set_ai_conn_name,
            ),

            # ── 2. Endpoint ───────────────────────────────────────
            _current_connection_edit_field(
                "Endpoint",
                rx.cond(SettingsState.ai_saved_endpoint != "", SettingsState.ai_saved_endpoint, "Not configured"),
                SettingsState.ai_conn_endpoint, SettingsState.set_ai_conn_endpoint,
            ),

            # ── 3. Model / Deployment ─────────────────────────────
            _current_connection_edit_field(
                "Model / Deployment",
                rx.cond(SettingsState.ai_saved_model != "", SettingsState.ai_saved_model, "Not configured"),
                SettingsState.ai_conn_model, SettingsState.set_ai_conn_model,
            ),

            # ── 4. API Version ────────────────────────────────────
            _current_connection_edit_field(
                "API Version",
                rx.cond(SettingsState.ai_saved_api_version != "", SettingsState.ai_saved_api_version, "Not configured"),
                SettingsState.ai_conn_api_version, SettingsState.set_ai_conn_api_version,
            ),

            # ── 5. CA Certificate ─────────────────────────────────
            _current_connection_edit_field(
                "CA Certificate", SettingsState.ai_saved_cert,
                SettingsState.ai_conn_cert, SettingsState.set_ai_conn_cert,
            ),

            # ── 6. API Key ─────────────────────────────────────────
            _current_connection_api_key(),

            # ── 7. Last Tested ────────────────────────────────────
            _ai_display_field("Last Tested", SettingsState.ai_saved_last_tested),

            # ── 8. Connection Status ──────────────────────────────
            rx.vstack(
                rx.text("Status", font_family=FONT_BODY, size="2",
                        weight="medium", color=COLORS["ink"]),
                rx.box(
                    rx.cond(
                        SettingsState.ai_saved_status == "success",
                        rx.hstack(
                            rx.icon("circle-check", size=14, color="#16A34A"),
                            rx.text("Connection Successful",
                                    font_family=FONT_BODY, size="2",
                                    color="#16A34A", weight="medium"),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.cond(
                            SettingsState.ai_saved_status == "error",
                            rx.hstack(
                                rx.icon("circle-x", size=14, color="#DC2626"),
                                rx.text("Connection Failed",
                                        font_family=FONT_BODY, size="2",
                                        color="#DC2626", weight="medium"),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.text("Not yet tested",
                                    font_family=FONT_BODY, size="2",
                                    color=COLORS["slate"],
                                    font_style="italic"),
                        ),
                    ),
                    background=rx.cond(
                        SettingsState.ai_saved_status == "success",
                        "#DCFCE7",
                        rx.cond(
                            SettingsState.ai_saved_status == "error",
                            "#FEF2F2",
                            "#F8FAFC",
                        ),
                    ),
                    border=rx.cond(
                        SettingsState.ai_saved_status == "success",
                        "1.5px solid #BBF7D0",
                        rx.cond(
                            SettingsState.ai_saved_status == "error",
                            "1.5px solid #FECACA",
                            f"1.5px solid {COLORS['line']}",
                        ),
                    ),
                    border_radius="8px",
                    padding="0.65em 0.9em",
                    width="100%",
                ),
                spacing="1", width="100%", align_items="stretch",
            ),

            # ── Action buttons ────────────────────────────────────
            rx.hstack(
                rx.cond(
                    SettingsState.ai_conn_editing_existing,
                    rx.button(
                        "Cancel",
                        on_click=SettingsState.ai_cancel_form,
                        variant="outline", color=COLORS["slate"],
                        border=f"1.5px solid {COLORS['line']}", background="white",
                        font_family=FONT_BODY, size="2", cursor="pointer",
                    ),
                    rx.button(
                        rx.icon("pencil", size=14), "Edit",
                        on_click=SettingsState.ai_edit_connection,
                        variant="outline", color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}", background="white",
                        font_family=FONT_BODY, size="2", cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                    ),
                ),
                rx.button(
                    rx.icon("radio", size=14),
                    "Test Connection",
                    on_click=SettingsState.ai_test_connection,
                    variant="outline",
                    color=COLORS["ink"],
                    border=f"1.5px solid {COLORS['line']}",
                    background="white",
                    font_family=FONT_BODY,
                    size="2",
                    cursor="pointer",
                    _hover={"background": COLORS["canvas"]},
                ),
                rx.button(
                    rx.icon("check", size=14), "Save and Use",
                    on_click=SettingsState.ai_save_and_use,
                    disabled=~SettingsState.ai_conn_editing_existing,
                    background=COLORS["primary"], color="white",
                    font_family=FONT_BODY, size="2", cursor="pointer",
                    _hover={"background": COLORS["primary_hover"]},
                ),
                spacing="3",
                align_items="center",
                padding_top="0.5em",
            ),

            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.75em",
        width="100%",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.04)",
    )


# ─────────────────────────────────────────────────────────────
# Access Control Component & Dialogs
# ─────────────────────────────────────────────────────────────

def _admin_account_row(admin: dict, idx: int) -> rx.Component:

    return rx.table.row(
        # 1. #
        rx.table.cell(
            rx.text(admin["num"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
            vertical_align="middle",
            width="8%",
        ),
        # 2. Username
        rx.table.cell(
            rx.text(admin["username"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
            vertical_align="middle",
            width="28%",
        ),
        # 3. Role
        rx.table.cell(
            rx.text(admin["role"], font_family=FONT_BODY, size="2", color=COLORS["ink"]),
            vertical_align="middle",
            width="30%",
        ),
        # 4. Actions
        rx.table.cell(
            rx.cond(
                admin["is_master"],
                rx.hstack(
                    rx.text("—", color=COLORS["slate"], font_family=FONT_BODY, size="2"),
                    rx.text("Cannot be edited or removed", color=COLORS["slate"], font_family=FONT_BODY, size="1"),
                    spacing="3",
                    align_items="center",
                ),
                rx.hstack(
                    rx.hstack(
                        rx.icon("pencil", size=14, color="#4F46E5"),
                        rx.text("Edit", font_family=FONT_BODY, size="2", weight="medium", color="#4F46E5"),
                        spacing="1",
                        align_items="center",
                        cursor="pointer",
                        _hover={"opacity": 0.8},
                        on_click=SettingsState.open_edit_admin_dialog(idx),
                    ),
                    rx.hstack(
                        rx.icon("eye", size=14, color="#7C3AED"),
                        rx.text("View", font_family=FONT_BODY, size="2", weight="medium", color="#7C3AED"),
                        spacing="1",
                        align_items="center",
                        cursor="pointer",
                        _hover={"opacity": 0.8},
                        on_click=SettingsState.open_view_admin_dialog(idx),
                    ),
                    rx.hstack(
                        rx.icon("trash-2", size=14, color="#DC2626"),
                        rx.text("Delete", font_family=FONT_BODY, size="2", weight="medium", color="#DC2626"),
                        spacing="1",
                        align_items="center",
                        cursor="pointer",
                        _hover={"opacity": 0.8},
                        on_click=SettingsState.open_delete_admin_dialog(idx),
                    ),
                    spacing="4",
                    align_items="center",
                ),
            ),
            vertical_align="middle",
            width="34%",
        ),
        style={
            "&:hover": {"background": "#F8FAFC"},
            "transition": "background 0.12s ease",
            "borderBottom": f"1px solid {COLORS['line']}",
        },
    )


def access_control_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Section Header Row
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("users-round", size=20, color="#4F46E5"),
                        background="#EEF2FF",
                        padding="0.7em",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.text(
                            "Access Control",
                            font_family=FONT_BODY,
                            size="3",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "Manage administrator accounts. Master admin can add, edit and remove other administrators.",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=15),
                    "Add Admin",
                    background="#4F46E5",
                    color="white",
                    font_family=FONT_BODY,
                    font_size="13px",
                    font_weight="medium",
                    border_radius="8px",
                    padding="0.5em 1.2em",
                    cursor="pointer",
                    _hover={"background": "#4338CA"},
                    transition="all 0.15s ease",
                    on_click=SettingsState.open_add_admin_dialog,
                ),
                width="100%",
                align_items="center",
                padding_bottom="1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
            ),

            # Administrator Table
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("#", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                width="8%",
                            ),
                            rx.table.column_header_cell(
                                rx.text("Username", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                width="28%",
                            ),
                            rx.table.column_header_cell(
                                rx.text("Role", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                width="30%",
                            ),
                            rx.table.column_header_cell(
                                rx.text("Actions", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                width="34%",
                            ),
                            style={"background": "#F5F3FF"},
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(SettingsState.admin_accounts, _admin_account_row)
                    ),
                    width="100%",
                ),
                border=f"1px solid {COLORS['line']}",
                border_radius="10px",
                overflow="hidden",
                width="100%",
            ),

            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.75em",
        width="100%",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.04)",
    )


def add_admin_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("user-plus", size=22, color="#4F46E5"),
                            background="#EEF2FF",
                            padding="0.65em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text(
                                "Add New Admin",
                                font_family=FONT_BODY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Create a new administrator account.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.box(
                            rx.icon("x", size=18, color=COLORS["slate"]),
                            cursor="pointer",
                            padding="0.35em",
                            border_radius="6px",
                            _hover={"background": COLORS["canvas"], "color": COLORS["ink"]},
                            transition="all 0.15s ease",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            on_click=SettingsState.close_add_admin_dialog,
                        )
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.6em",
                ),

                # Error banner
                rx.cond(
                    SettingsState.add_admin_error != "",
                    rx.box(
                        rx.text(
                            SettingsState.add_admin_error,
                            font_family=FONT_BODY,
                            size="2",
                            color="#DC2626",
                        ),
                        background="#FEF2F2",
                        border="1px solid #FECACA",
                        border_radius="8px",
                        padding="0.6em 0.9em",
                        width="100%",
                    ),
                    rx.fragment(),
                ),

                # Form Fields - Vertical Stack
                rx.vstack(
                    # Row 1: Username
                    rx.vstack(
                        _ai_field_label("Username", required=True),
                        rx.input(
                            placeholder="Enter username",
                            value=SettingsState.new_admin_username,
                            on_change=SettingsState.set_new_admin_username,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    # Row 2: Password
                    rx.vstack(
                        _ai_field_label("Password", required=True),
                        rx.input(
                            rx.input.slot(
                                rx.cond(
                                    SettingsState.show_new_admin_password,
                                    rx.icon("eye-off", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_new_admin_password),
                                    rx.icon("eye", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_new_admin_password),
                                ),
                                side="right",
                            ),
                            type=rx.cond(SettingsState.show_new_admin_password, "text", "password"),
                            placeholder="Enter password",
                            value=SettingsState.new_admin_password,
                            on_change=SettingsState.set_new_admin_password,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    # Row 3: Confirm Password
                    rx.vstack(
                        _ai_field_label("Confirm Password", required=True),
                        rx.input(
                            rx.input.slot(
                                rx.cond(
                                    SettingsState.show_new_admin_confirm_password,
                                    rx.icon("eye-off", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_new_admin_confirm_password),
                                    rx.icon("eye", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_new_admin_confirm_password),
                                ),
                                side="right",
                            ),
                            type=rx.cond(SettingsState.show_new_admin_confirm_password, "text", "password"),
                            placeholder="Confirm password",
                            value=SettingsState.new_admin_confirm_password,
                            on_change=SettingsState.set_new_admin_confirm_password,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),

                # Footer Buttons
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Cancel",
                        on_click=SettingsState.close_add_admin_dialog,
                        variant="outline",
                        color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}",
                        background="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    rx.button(
                        rx.icon("user-plus", size=15),
                        "Create Admin",
                        on_click=SettingsState.create_admin,
                        background="#4F46E5",
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": "#4338CA"},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "480px"},
            background="white",
            border_radius="14px",
            padding="1.6em",
        ),
        open=SettingsState.show_add_admin_dialog,
        on_open_change=SettingsState.set_show_add_admin_dialog,
    )


def edit_admin_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("pencil", size=22, color="#4F46E5"),
                            background="#EEF2FF",
                            padding="0.65em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text(
                                "Edit Admin",
                                font_family=FONT_BODY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Update administrator account details.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.box(
                            rx.icon("x", size=18, color=COLORS["slate"]),
                            cursor="pointer",
                            padding="0.35em",
                            border_radius="6px",
                            _hover={"background": COLORS["canvas"], "color": COLORS["ink"]},
                            transition="all 0.15s ease",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            on_click=SettingsState.close_edit_admin_dialog,
                        )
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.6em",
                ),

                # Error banner
                rx.cond(
                    SettingsState.edit_admin_error != "",
                    rx.box(
                        rx.text(
                            SettingsState.edit_admin_error,
                            font_family=FONT_BODY,
                            size="2",
                            color="#DC2626",
                        ),
                        background="#FEF2F2",
                        border="1px solid #FECACA",
                        border_radius="8px",
                        padding="0.6em 0.9em",
                        width="100%",
                    ),
                    rx.fragment(),
                ),

                # Form Fields - Vertical Stack
                rx.vstack(
                    # Row 1: Username
                    rx.vstack(
                        _ai_field_label("Username", required=True),
                        rx.input(
                            placeholder="Enter username",
                            value=SettingsState.edit_admin_username,
                            on_change=SettingsState.set_edit_admin_username,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    # Row 2: Password
                    rx.vstack(
                        rx.text("Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            rx.input.slot(
                                rx.cond(
                                    SettingsState.show_edit_admin_password,
                                    rx.icon("eye-off", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_edit_admin_password),
                                    rx.icon("eye", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_edit_admin_password),
                                ),
                                side="right",
                            ),
                            type=rx.cond(SettingsState.show_edit_admin_password, "text", "password"),
                            placeholder="Enter new password",
                            value=SettingsState.edit_admin_password,
                            on_change=SettingsState.set_edit_admin_password,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    # Row 3: Confirm Password
                    rx.vstack(
                        rx.text("Confirm Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            rx.input.slot(
                                rx.cond(
                                    SettingsState.show_edit_admin_confirm_password,
                                    rx.icon("eye-off", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_edit_admin_confirm_password),
                                    rx.icon("eye", size=16, color=COLORS["slate"], cursor="pointer", on_click=SettingsState.toggle_edit_admin_confirm_password),
                                ),
                                side="right",
                            ),
                            type=rx.cond(SettingsState.show_edit_admin_confirm_password, "text", "password"),
                            placeholder="Confirm new password",
                            value=SettingsState.edit_admin_confirm_password,
                            on_change=SettingsState.set_edit_admin_confirm_password,
                            font_family=FONT_BODY,
                            size="2",
                            width="100%",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.65em 0.9em",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),

                # Footer Buttons
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Cancel",
                        on_click=SettingsState.close_edit_admin_dialog,
                        variant="outline",
                        color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}",
                        background="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    rx.button(
                        rx.icon("save", size=15),
                        "Save Changes",
                        on_click=SettingsState.save_admin_changes,
                        background="#4F46E5",
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": "#4338CA"},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "560px"},
            background="white",
            border_radius="14px",
            padding="1.6em",
        ),
        open=SettingsState.show_edit_admin_dialog,
        on_open_change=SettingsState.set_show_edit_admin_dialog,
    )


def delete_admin_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("trash-2", size=22, color="#DC2626"),
                            background="#FEE2E2",
                            padding="0.65em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.text(
                            "Delete Admin",
                            font_family=FONT_BODY,
                            size="4",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.box(
                            rx.icon("x", size=18, color=COLORS["slate"]),
                            cursor="pointer",
                            padding="0.35em",
                            border_radius="6px",
                            _hover={"background": COLORS["canvas"], "color": COLORS["ink"]},
                            transition="all 0.15s ease",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            on_click=SettingsState.close_delete_admin_dialog,
                        )
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.6em",
                ),

                # Message & Warning
                rx.vstack(
                    rx.text(
                        "Are you sure you want to delete this admin account?",
                        font_family=FONT_BODY,
                        size="2",
                        weight="medium",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "This action cannot be undone.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                    width="100%",
                ),

                # Username display box
                rx.box(
                    rx.vstack(
                        rx.text(
                            "Username",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        rx.text(
                            SettingsState.delete_admin_username,
                            font_family=FONT_BODY,
                            size="3",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    background="#F8FAFC",
                    border=f"1.5px solid {COLORS['line']}",
                    border_radius="8px",
                    padding="0.8em 1em",
                    width="100%",
                ),

                # Footer Buttons
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Cancel",
                        on_click=SettingsState.close_delete_admin_dialog,
                        variant="outline",
                        color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}",
                        background="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    rx.button(
                        "Delete",
                        on_click=SettingsState.confirm_delete_admin,
                        background="#DC2626",
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": "#B91C1C"},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "480px"},
            background="white",
            border_radius="14px",
            padding="1.6em",
        ),
        open=SettingsState.show_delete_admin_dialog,
        on_open_change=SettingsState.set_show_delete_admin_dialog,
    )


def view_admin_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("eye", size=22, color="#7C3AED"),
                            background="#F3E8FF",
                            padding="0.65em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text(
                                "View Admin Credentials",
                                font_family=FONT_BODY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Admin account details (read-only).",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.box(
                            rx.icon("x", size=18, color=COLORS["slate"]),
                            cursor="pointer",
                            padding="0.35em",
                            border_radius="6px",
                            _hover={"background": COLORS["canvas"]},
                            transition="all 0.15s ease",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            on_click=SettingsState.close_view_admin_dialog,
                        )
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Username Field
                rx.vstack(
                    rx.text("Username", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                    rx.input(
                        value=SettingsState.view_admin_username,
                        read_only=True,
                        font_family=FONT_BODY,
                        size="2",
                        width="100%",
                        background="#F8FAFC",
                        border=f"1.5px solid {COLORS['line']}",
                        border_radius="8px",
                        color=COLORS["ink"],
                        cursor="default",
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),

                # Password Field
                rx.vstack(
                    rx.text("Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                    rx.input(
                        rx.input.slot(
                            rx.icon_button(
                                rx.cond(
                                    SettingsState.view_admin_show_password,
                                    rx.icon("eye-off", size=15),
                                    rx.icon("eye", size=15),
                                ),
                                size="1",
                                variant="ghost",
                                color=COLORS["slate"],
                                cursor="pointer",
                                type="button",
                                tab_index=-1,
                                on_click=SettingsState.toggle_view_admin_show_password,
                                _hover={"color": COLORS["ink"], "background": "transparent"},
                                style={
                                    "background": "transparent",
                                    "border": "none",
                                    "box_shadow": "none",
                                    "padding": "0",
                                },
                            ),
                            side="right",
                        ),
                        type=rx.cond(SettingsState.view_admin_show_password, "text", "password"),
                        value=rx.cond(
                            SettingsState.view_admin_password != "",
                            SettingsState.view_admin_password,
                            "Password unavailable",
                        ),
                        read_only=True,
                        font_family=FONT_BODY,
                        size="2",
                        width="100%",
                        background="#F8FAFC",
                        border=f"1.5px solid {COLORS['line']}",
                        border_radius="8px",
                        color=COLORS["ink"],
                        cursor="default",
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),

                # Info Box
                rx.hstack(
                    rx.icon("info", size=15, color="#7C3AED"),
                    rx.text(
                        "This is a view-only mode. You cannot edit the credentials here.",
                        font_family=FONT_BODY,
                        size="2",
                        color="#5B21B6",
                    ),
                    background="#F5F3FF",
                    border="1px solid #DDD6FE",
                    border_radius="8px",
                    padding="0.65em 0.9em",
                    spacing="2",
                    align_items="center",
                    width="100%",
                ),

                # Footer
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Close",
                        on_click=SettingsState.close_view_admin_dialog,
                        variant="outline",
                        color=COLORS["ink"],
                        border=f"1.5px solid {COLORS['line']}",
                        background="white",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                        border_radius="8px",
                        padding="0.5em 1.4em",
                    ),
                    width="100%",
                    padding_top="0.4em",
                    border_top=f"1px solid {COLORS['line']}",
                    align_items="center",
                ),

                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "460px"},
            background="white",
            border_radius="14px",
            padding="1.6em",
        ),
        open=SettingsState.show_view_admin_dialog,
        on_open_change=SettingsState.set_show_view_admin_dialog,
    )


# ─────────────────────────────────────────────────────────────
# Settings page entry point
# ─────────────────────────────────────────────────────────────

def settings_page() -> rx.Component:
    content = rx.vstack(
        # ── Page Header ───────────────────────────────────────
        rx.vstack(
            rx.text(
                "Settings",
                font_family=FONT_DISPLAY,
                size="6",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "Manage system settings and administrator accounts.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            spacing="1",
            align_items="start",
            padding_bottom="0.5em",
        ),

        # ── Back to Settings button (shown when in a connection sub-view) ──
        rx.cond(
            SettingsState.active_view != "select",
            rx.button(
                rx.icon("arrow-left", size=14),
                "Back to Settings",
                on_click=SettingsState.open_selection_dialog,
                variant="ghost",
                color=COLORS["slate"],
                font_family=FONT_BODY,
                size="2",
                cursor="pointer",
                padding_left="0",
                _hover={"color": COLORS["ink"]},
            ),
            rx.fragment(),
        ),

        # ── Connection Card View ──────────────────────────────
        rx.cond(
            SettingsState.active_view == "new",
            _new_connection_card(),
            rx.cond(
                SettingsState.active_view == "current",
                _current_connection_card(),
                _selection_view_card(),
            ),
        ),

        # ── Access Control Section (only visible on main/select view) ──
        rx.cond(
            SettingsState.active_view == "select",
            access_control_card(),
            rx.fragment(),
        ),

        # ── Admin Dialogs ─────────────────────────────────────
        add_admin_dialog(),
        edit_admin_dialog(),
        delete_admin_dialog(),
        view_admin_dialog(),

        spacing="5",
        width="100%",
        align_items="stretch",
    )

    return admin_shell(
        active="settings",
        title="Settings",
        subtitle="Manage system settings and administrator accounts.",
        content=content,
    )
