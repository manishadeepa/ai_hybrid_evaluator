import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.components.auth.auth_card import auth_card
from ai_hybrid_evaluator.components.auth.auth_header import auth_header
from ai_hybrid_evaluator.components.auth.auth_input import auth_input
from ai_hybrid_evaluator.components.auth.auth_button import auth_button
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def _forgot_password_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.text(
                "Forgot Password?",
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["primary"],
                cursor="pointer",
                _hover={"text_decoration": "underline"},
            ),
        ),
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("key-round", size=20, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.5em",
                        border_radius="50%",
                    ),
                    rx.vstack(
                        rx.dialog.title("Reset Admin Password"),
                        rx.dialog.description(
                            "Enter your official @tvsmotor.com email address to receive password reset instructions.",
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                rx.vstack(
                    rx.text(
                        "Official Email (@tvsmotor.com)",
                        font_family=FONT_BODY,
                        size="2",
                        weight="medium",
                        color=COLORS["ink"],
                    ),
                    rx.input(
                        placeholder="admin@tvsmotor.com",
                        width="100%",
                        size="3",
                        border=f"1.5px solid {COLORS['line']}",
                        border_radius="10px",
                        background=COLORS["surface"],
                    ),
                    spacing="1",
                    width="100%",
                    padding_top="0.8em",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="outline",
                            color_scheme="gray",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                    ),
                    rx.dialog.close(
                        rx.button(
                            "Send Reset Link",
                            on_click=rx.toast.success("Password reset instructions sent to your @tvsmotor.com email."),
                            background=COLORS["primary"],
                            color="white",
                            font_family=FONT_BODY,
                            size="2",
                            _hover={"background": COLORS["primary_hover"]},
                        ),
                    ),
                    spacing="3",
                    width="100%",
                    padding_top="1.2em",
                ),
                spacing="2",
                width="100%",
            ),
            max_width="440px",
            padding="1.8em",
            border_radius="14px",
        ),
    )


def _change_password_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.text(
                "Change Password",
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["primary"],
                cursor="pointer",
                _hover={"text_decoration": "underline"},
            ),
        ),
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("lock", size=20, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.5em",
                        border_radius="50%",
                    ),
                    rx.vstack(
                        rx.dialog.title("Change Admin Password"),
                        rx.dialog.description(
                            "Update the password for your existing TVS administrative account.",
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                rx.vstack(
                    rx.vstack(
                        rx.text("Official Email (@tvsmotor.com)", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            placeholder="admin@tvsmotor.com",
                            width="100%",
                            size="3",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="10px",
                            background=COLORS["surface"],
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Current Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            type="password",
                            placeholder="Enter current password",
                            width="100%",
                            size="3",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="10px",
                            background=COLORS["surface"],
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("New Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            type="password",
                            placeholder="Enter new password",
                            width="100%",
                            size="3",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="10px",
                            background=COLORS["surface"],
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Confirm New Password", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.input(
                            type="password",
                            placeholder="Confirm new password",
                            width="100%",
                            size="3",
                            border=f"1.5px solid {COLORS['line']}",
                            border_radius="10px",
                            background=COLORS["surface"],
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                    padding_top="0.8em",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="outline",
                            color_scheme="gray",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                    ),
                    rx.dialog.close(
                        rx.button(
                            "Update Password",
                            on_click=rx.toast.success("Admin password updated successfully. Please login with your new password."),
                            background=COLORS["primary"],
                            color="white",
                            font_family=FONT_BODY,
                            size="2",
                            _hover={"background": COLORS["primary_hover"]},
                        ),
                    ),
                    spacing="3",
                    width="100%",
                    padding_top="1.2em",
                ),
                spacing="2",
                width="100%",
            ),
            max_width="460px",
            padding="1.8em",
            border_radius="14px",
        ),
    )


def login_page() -> rx.Component:
    content = rx.vstack(
        auth_header(
            "Admin Sign In",
            "Sign in to access the GenAI Hybrid Evaluator Administration Portal.",
        ),
        auth_input(
            "Official Email (@tvsmotor.com)",
            "admin@tvsmotor.com",
            AuthState.signin_email,
            AuthState.set_signin_email,
        ),
        rx.box(
            auth_input(
                "Password",
                "Enter your password",
                AuthState.signin_password,
                AuthState.set_signin_password,
                input_type="password",
            ),
            width="100%",
            padding_top="1.1em",
        ),
        rx.hstack(
            _forgot_password_dialog(),
            rx.spacer(),
            _change_password_dialog(),
            width="100%",
            padding_top="0.6em",
            align_items="center",
        ),
        rx.cond(
            AuthState.signin_error != "",
            rx.box(
                rx.text(
                    AuthState.signin_error,
                    color=COLORS["danger"],
                    size="2",
                    font_family=FONT_BODY,
                ),
                padding_top="0.85em",
            ),
        ),
        rx.box(
            auth_button("Login", AuthState.sign_in),
            padding_top="1.6em",
            width="100%",
        ),
        width="100%",
        align_items="stretch",
    )
    return auth_card(content)