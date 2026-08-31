"""Admin Settings page — profile, preferences, and notification controls."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


# ─────────────────────────────────────────────────────────────
# Settings state
# ─────────────────────────────────────────────────────────────

class SettingsState(rx.State):
    # Admin profile
    admin_full_name: str = "Admin"
    admin_email: str = "admin@genaievaluator.com"
    admin_current_password: str = ""
    admin_new_password: str = ""
    admin_confirm_password: str = ""
    profile_save_error: str = ""

    # Notification preferences
    notif_new_assessment: bool = True
    notif_facilitator_response: bool = True
    notif_candidate_added: bool = False
    notif_score_submitted: bool = True
    notif_email_digest: bool = False

    # App preferences
    app_name: str = "AI Hybrid Evaluator"
    pass_threshold: str = "60"
    timezone: str = "Asia/Kolkata"

    # Setters — profile
    def set_admin_full_name(self, v: str): self.admin_full_name = v
    def set_admin_email(self, v: str): self.admin_email = v
    def set_admin_current_password(self, v: str): self.admin_current_password = v
    def set_admin_new_password(self, v: str): self.admin_new_password = v
    def set_admin_confirm_password(self, v: str): self.admin_confirm_password = v

    # Setters — notifications
    def toggle_notif_new_assessment(self, v: bool): self.notif_new_assessment = v
    def toggle_notif_facilitator_response(self, v: bool): self.notif_facilitator_response = v
    def toggle_notif_candidate_added(self, v: bool): self.notif_candidate_added = v
    def toggle_notif_score_submitted(self, v: bool): self.notif_score_submitted = v
    def toggle_notif_email_digest(self, v: bool): self.notif_email_digest = v

    # Setters — app preferences
    def set_app_name(self, v: str): self.app_name = v
    def set_pass_threshold(self, v: str): self.pass_threshold = v
    def set_timezone(self, v: str): self.timezone = v

    def save_profile(self):
        self.profile_save_error = ""
        if not self.admin_full_name or not self.admin_email:
            self.profile_save_error = "Name and email are required."
            return
        if self.admin_new_password:
            if not self.admin_current_password:
                self.profile_save_error = "Enter your current password to set a new one."
                return
            if self.admin_new_password != self.admin_confirm_password:
                self.profile_save_error = "New passwords do not match."
                return
            if len(self.admin_new_password) < 6:
                self.profile_save_error = "New password must be at least 6 characters."
                return
        # Reset password fields on success
        self.admin_current_password = ""
        self.admin_new_password = ""
        self.admin_confirm_password = ""
        return rx.toast.success("Profile saved successfully!")

    def save_preferences(self):
        return rx.toast.success("Preferences saved!")

    def save_notifications(self):
        return rx.toast.success("Notification settings saved!")


# ─────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────

def section_card(title: str, subtitle: str, icon: str, body: rx.Component) -> rx.Component:
    return rx.box(
        rx.vstack(
            # Section header
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=18, color=COLORS["primary"]),
                    background=COLORS["primary_soft"],
                    padding="0.6em",
                    border_radius="8px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text(title, font_family=FONT_BODY, size="3",
                            weight="bold", color=COLORS["ink"]),
                    rx.text(subtitle, font_family=FONT_BODY, size="1",
                            color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                padding_bottom="1em",
                border_bottom=f"1px solid {COLORS['line']}",
                width="100%",
            ),
            # Body
            body,
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.5em",
        width="100%",
    )


def settings_input(label: str, placeholder: str, value: rx.Var,
                   on_change, input_type: str = "text") -> rx.Component:
    return rx.vstack(
        rx.text(label, font_family=FONT_BODY, size="2",
                weight="medium", color=COLORS["ink"]),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=input_type,
            width="100%",
            size="3",
            background=COLORS["surface"],
            border=f"1.5px solid {COLORS['line']}",
            _focus={"border_color": COLORS["primary"],
                    "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
            font_family=FONT_BODY,
        ),
        spacing="1",
        width="100%",
        align_items="stretch",
    )


def toggle_row(label: str, description: str, checked: rx.Var,
               on_change) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(label, font_family=FONT_BODY, size="2",
                    weight="medium", color=COLORS["ink"]),
            rx.text(description, font_family=FONT_BODY, size="1",
                    color=COLORS["slate"]),
            spacing="0",
            align_items="start",
            flex="1",
        ),
        rx.switch(
            checked=checked,
            on_change=on_change,
            color_scheme="indigo",
        ),
        justify="between",
        align_items="center",
        width="100%",
        padding="0.8em 0",
        border_bottom=f"1px solid {COLORS['line']}",
    )


# ─────────────────────────────────────────────────────────────
# Settings page
# ─────────────────────────────────────────────────────────────

def settings_page() -> rx.Component:
    content = rx.vstack(

        # ── Admin Profile ─────────────────────────────────────────────
        section_card(
            "Admin Profile",
            "Update your name, email, and password.",
            "user-cog",
            rx.vstack(
                rx.grid(
                    settings_input(
                        "Full Name", "Enter your full name",
                        SettingsState.admin_full_name,
                        SettingsState.set_admin_full_name,
                    ),
                    settings_input(
                        "Email Address", "Enter your email",
                        SettingsState.admin_email,
                        SettingsState.set_admin_email,
                        "email",
                    ),
                    columns="2", spacing="4", width="100%",
                ),
                # Divider
                rx.box(height="1px", background=COLORS["line"], width="100%",
                       margin="0.5em 0"),
                rx.text("Change Password", font_family=FONT_BODY, size="2",
                        weight="bold", color=COLORS["ink"]),
                rx.grid(
                    settings_input(
                        "Current Password", "••••••••",
                        SettingsState.admin_current_password,
                        SettingsState.set_admin_current_password,
                        "password",
                    ),
                    settings_input(
                        "New Password", "Min. 6 characters",
                        SettingsState.admin_new_password,
                        SettingsState.set_admin_new_password,
                        "password",
                    ),
                    settings_input(
                        "Confirm New Password", "Repeat new password",
                        SettingsState.admin_confirm_password,
                        SettingsState.set_admin_confirm_password,
                        "password",
                    ),
                    rx.box(),  # grid spacer
                    columns="2", spacing="4", width="100%",
                ),
                # Error
                rx.cond(
                    SettingsState.profile_save_error != "",
                    rx.text(SettingsState.profile_save_error,
                            font_family=FONT_BODY, size="2",
                            color=COLORS["danger"]),
                ),
                # Save button
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.icon("save", size=14), "Save Profile",
                        on_click=SettingsState.save_profile,
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    width="100%",
                ),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),
        ),

        # ── App Preferences ───────────────────────────────────────────
        section_card(
            "App Preferences",
            "Configure platform-level settings.",
            "settings",
            rx.vstack(
                rx.grid(
                    settings_input(
                        "Application Name", "e.g. AI Hybrid Evaluator",
                        SettingsState.app_name,
                        SettingsState.set_app_name,
                    ),
                    settings_input(
                        "Default Pass Threshold (%)",
                        "e.g. 60",
                        SettingsState.pass_threshold,
                        SettingsState.set_pass_threshold,
                        "number",
                    ),
                    rx.vstack(
                        rx.text("Timezone", font_family=FONT_BODY, size="2",
                                weight="medium", color=COLORS["ink"]),
                        rx.select(
                            ["Asia/Kolkata", "UTC", "America/New_York",
                             "Europe/London", "Asia/Singapore"],
                            value=SettingsState.timezone,
                            on_change=SettingsState.set_timezone,
                            width="100%",
                            size="3",
                        ),
                        spacing="1", width="100%", align_items="stretch",
                    ),
                    rx.box(),  # grid spacer
                    columns="2", spacing="4", width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.icon("save", size=14), "Save Preferences",
                        on_click=SettingsState.save_preferences,
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    width="100%",
                ),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),
        ),

        # ── Notifications ─────────────────────────────────────────────
        section_card(
            "Notification Preferences",
            "Choose which events trigger in-app notifications.",
            "bell",
            rx.vstack(
                toggle_row(
                    "New Assessment Created",
                    "Notify when admin creates a new assessment.",
                    SettingsState.notif_new_assessment,
                    SettingsState.toggle_notif_new_assessment,
                ),
                toggle_row(
                    "Facilitator Response",
                    "Notify when a facilitator approves or declines an assessment.",
                    SettingsState.notif_facilitator_response,
                    SettingsState.toggle_notif_facilitator_response,
                ),
                toggle_row(
                    "Candidate Added",
                    "Notify when a new candidate is registered.",
                    SettingsState.notif_candidate_added,
                    SettingsState.toggle_notif_candidate_added,
                ),
                toggle_row(
                    "Scores Submitted",
                    "Notify when a facilitator submits evaluation scores.",
                    SettingsState.notif_score_submitted,
                    SettingsState.toggle_notif_score_submitted,
                ),
                toggle_row(
                    "Daily Email Digest",
                    "Receive a daily email summary of all activity.",
                    SettingsState.notif_email_digest,
                    SettingsState.toggle_notif_email_digest,
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.icon("bell", size=14), "Save Notifications",
                        on_click=SettingsState.save_notifications,
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="0",
                width="100%",
                align_items="stretch",
            ),
        ),

        spacing="5",
        width="100%",
        align_items="stretch",
        max_width="820px",
    )

    return admin_shell(
        active="settings",
        title="Settings",
        subtitle="Manage your admin profile, app preferences, and notification settings.",
        content=content,
    )