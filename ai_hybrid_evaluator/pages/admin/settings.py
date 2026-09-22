"""Admin Settings page — AI Connection Settings."""

import reflex as rx
from datetime import datetime
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────
# Settings state
# ─────────────────────────────────────────────────────────────

class SettingsState(rx.State):
    # ── View mode: "select" (initial) | "new" | "current" ─────
    active_view: str = "select"
    show_selection_dialog: bool = True

    # ── AI Connection form fields ─────────────────────────────
    ai_conn_name: str = ""
    ai_conn_endpoint: str = ""
    ai_conn_model: str = ""
    ai_conn_api_version: str = ""
    ai_conn_cert: str = ""
    ai_conn_api_key: str = ""
    ai_conn_show_key: bool = False   # toggle API key visibility in the form

    # ── Saved AI Connection (populated or default active) ────
    ai_saved_name: str = "Azure-OpenAI (Prod)"
    ai_saved_endpoint: str = "https://my-resource.openai.azure.com"
    ai_saved_model: str = "gpt-4o"
    ai_saved_api_version: str = "2024-02-15-preview"
    ai_saved_cert: str = "Not configured"
    ai_saved_last_tested: str = "Aug 31, 2026, 09:15 AM"
    ai_saved_status: str = "success"        # "success" | "error" | ""
    ai_saved_show_key: bool = False         # toggle masked key in current connection view

    # ── Navigation / Selection methods ────────────────────────
    def set_show_selection_dialog(self, v: bool):
        self.show_selection_dialog = v

    def open_selection_dialog(self):
        self.show_selection_dialog = True
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
    def set_ai_conn_api_key(self, v: str): self.ai_conn_api_key = v
    def toggle_ai_conn_show_key(self): self.ai_conn_show_key = not self.ai_conn_show_key
    def toggle_ai_saved_show_key(self): self.ai_saved_show_key = not self.ai_saved_show_key

    # ── AI Connection actions ─────────────────────────────────
    def ai_test_connection(self):
        """Simulate a connection test."""
        now_str = datetime.now().strftime("%b %d, %Y, %I:%M %p")
        self.ai_saved_last_tested = now_str
        self.ai_saved_status = "success"
        return rx.toast.success("Connection successful!")

    def ai_save_and_use(self):
        """Save the form data as the active AI connection."""
        if not self.ai_conn_name.strip():
            return rx.toast.error("Connection Name is required.")
        if not self.ai_conn_api_key.strip():
            return rx.toast.error("API Key is required.")

        self.ai_saved_name = self.ai_conn_name.strip()
        self.ai_saved_endpoint = self.ai_conn_endpoint.strip()
        self.ai_saved_model = self.ai_conn_model.strip()
        self.ai_saved_api_version = self.ai_conn_api_version.strip()
        self.ai_saved_cert = self.ai_conn_cert.strip() if self.ai_conn_cert.strip() else "Not configured"
        self.ai_saved_last_tested = datetime.now().strftime("%b %d, %Y, %I:%M %p")
        self.ai_saved_status = "success"

        # Clear the form and transition to current view
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_api_key = ""
        self.ai_conn_show_key = False
        self.active_view = "current"
        self.show_selection_dialog = False
        return rx.toast.success("AI Connection saved and activated!")

    def ai_cancel_form(self):
        """Clear the new-connection form and return to selection."""
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_api_key = ""
        self.ai_conn_show_key = False
        self.active_view = "select"
        self.show_selection_dialog = True

    def ai_replace_connection(self):
        """Transition from current connection to the new connection form."""
        self.ai_conn_name = ""
        self.ai_conn_endpoint = ""
        self.ai_conn_model = ""
        self.ai_conn_api_version = ""
        self.ai_conn_cert = ""
        self.ai_conn_api_key = ""
        self.ai_conn_show_key = False
        self.active_view = "new"
        self.show_selection_dialog = False


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
    """Read-only labelled display box for the Current Connection card."""
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

                # Option 2: Current AI Connection
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
                                "Current AI Connection",
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
                        rx.text("Current AI Connection", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
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
                rx.button(
                    rx.icon("arrow-left-right", size=13),
                    "Switch View",
                    on_click=SettingsState.open_selection_dialog,
                    size="1",
                    variant="ghost",
                    color=COLORS["slate"],
                    font_family=FONT_BODY,
                    cursor="pointer",
                    _hover={"color": "#4F46E5"},
                ),
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
                        value=SettingsState.ai_conn_api_key,
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
# 2. Current AI Connection Card
# ─────────────────────────────────────────────────────────────

def _current_connection_card() -> rx.Component:
    """Read-only card shown when user chooses Current AI Connection."""
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
                    rx.text("Current AI Connection",
                            font_family=FONT_BODY, size="3",
                            weight="bold", color=COLORS["ink"]),
                    rx.text("View and manage your active AI connection.",
                            font_family=FONT_BODY, size="1",
                            color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("arrow-left-right", size=13),
                    "Switch View",
                    on_click=SettingsState.open_selection_dialog,
                    size="1",
                    variant="ghost",
                    color=COLORS["slate"],
                    font_family=FONT_BODY,
                    cursor="pointer",
                    _hover={"color": "#4F46E5"},
                ),
                spacing="3",
                align_items="center",
                padding_bottom="1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
                width="100%",
            ),

            # ── 1. Connection Name ────────────────────────────────
            _ai_display_field("Connection Name", SettingsState.ai_saved_name),

            # ── 2. Endpoint ───────────────────────────────────────
            _ai_display_field(
                "Endpoint",
                rx.cond(
                    SettingsState.ai_saved_endpoint != "",
                    SettingsState.ai_saved_endpoint,
                    "Not configured",
                ),
            ),

            # ── 3. Model / Deployment ─────────────────────────────
            _ai_display_field(
                "Model / Deployment",
                rx.cond(
                    SettingsState.ai_saved_model != "",
                    SettingsState.ai_saved_model,
                    "Not configured",
                ),
            ),

            # ── 4. API Version ────────────────────────────────────
            _ai_display_field(
                "API Version",
                rx.cond(
                    SettingsState.ai_saved_api_version != "",
                    SettingsState.ai_saved_api_version,
                    "Not configured",
                ),
            ),

            # ── 5. CA Certificate ─────────────────────────────────
            _ai_display_field("CA Certificate", SettingsState.ai_saved_cert),

            # ── 6. Masked API Key ─────────────────────────────────
            rx.vstack(
                rx.text("API Key", font_family=FONT_BODY, size="2",
                        weight="medium", color=COLORS["ink"]),
                rx.hstack(
                    rx.box(
                        rx.cond(
                            SettingsState.ai_saved_show_key,
                            rx.text("(Key stored securely — not displayable)",
                                    font_family=FONT_BODY, size="2",
                                    color=COLORS["slate"],
                                    font_style="italic"),
                            rx.text("••••••••••••••••••••••••",
                                    font_family=FONT_BODY, size="2",
                                    color=COLORS["ink"],
                                    letter_spacing="2px"),
                        ),
                        background="#F8FAFC",
                        border=f"1.5px solid {COLORS['line']}",
                        border_radius="8px",
                        padding="0.65em 0.9em",
                        flex="1",
                    ),
                    rx.icon_button(
                        rx.cond(
                            SettingsState.ai_saved_show_key,
                            rx.icon("eye-off", size=16),
                            rx.icon("eye", size=16),
                        ),
                        on_click=SettingsState.toggle_ai_saved_show_key,
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
                    rx.icon("pencil", size=14),
                    "Replace with New Connection",
                    on_click=SettingsState.ai_replace_connection,
                    variant="outline",
                    color=COLORS["ink"],
                    border=f"1.5px solid {COLORS['line']}",
                    background="white",
                    font_family=FONT_BODY,
                    size="2",
                    cursor="pointer",
                    _hover={"background": COLORS["canvas"]},
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
# Settings page entry point
# ─────────────────────────────────────────────────────────────

def settings_page() -> rx.Component:
    content = rx.vstack(
        # ── Selection Dialog ──────────────────────────────────
        selection_dialog(),

        # ── Breadcrumb: Admin > Settings > AI Connection ─────
        rx.hstack(
            rx.text("Admin", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
            rx.icon("chevron-right", size=13, color=COLORS["slate"]),
            rx.text("Settings", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
            rx.icon("chevron-right", size=13, color=COLORS["slate"]),
            rx.text("AI Connection", font_family=FONT_BODY, size="2",
                    weight="bold", color="#4F46E5"),
            spacing="2",
            align_items="center",
        ),

        # ── Page Header ───────────────────────────────────────
        rx.vstack(
            rx.text(
                "AI Connection Settings",
                font_family=FONT_DISPLAY,
                size="6",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "Configure and manage the AI model connection used for evaluation.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            spacing="1",
            align_items="start",
            padding_bottom="0.5em",
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

        spacing="4",
        width="100%",
        align_items="stretch",
    )

    return admin_shell(
        active="settings",
        title="AI Connection Settings",
        subtitle="Configure and manage the AI model connection used for evaluation.",
        content=content,
    )