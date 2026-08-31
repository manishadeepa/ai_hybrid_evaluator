import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.components.auth.auth_card import auth_card
from ai_hybrid_evaluator.components.auth.auth_header import auth_header
from ai_hybrid_evaluator.components.auth.auth_input import auth_input
from ai_hybrid_evaluator.components.auth.auth_button import auth_button
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def _success_view() -> rx.Component:
    return rx.vstack(
        rx.center(
            rx.box(
                rx.icon("circle-check-big", size=36, color=COLORS["success"]),
                background=COLORS["success_soft"],
                border_radius="50%",
                padding="0.9em",
            ),
            width="100%",
            padding_bottom="1.2em",
        ),
        rx.heading(
            "Account created successfully.",
            size="5",
            weight="bold",
            font_family=FONT_BODY,
            color=COLORS["ink"],
            text_align="center",
        ),
        rx.text(
            "You can now sign in with your new credentials.",
            size="2",
            color=COLORS["slate"],
            font_family=FONT_BODY,
            text_align="center",
            padding_top="0.4em",
            padding_bottom="1.8em",
        ),
        auth_button("Continue to Sign In", AuthState.continue_to_signin),
        align_items="center",
        width="100%",
    )


def _form_view() -> rx.Component:
    return rx.vstack(
        auth_header(
            "Create admin account",
            "Set up institutional access to the evaluator platform.",
        ),
        auth_input("Username", "e.g. jane.doe", AuthState.signup_username, AuthState.set_signup_username),
        rx.box(
            auth_input("Employee ID", "e.g. EMP-1042", AuthState.signup_employee_id, AuthState.set_signup_employee_id),
            width="100%", padding_top="1.1em",
        ),
        rx.box(
            auth_input("Official Email", "you@yourorganization.com", AuthState.signup_email, AuthState.set_signup_email),
            width="100%", padding_top="1.1em",
        ),
        rx.box(
            auth_input("Password", "At least 8 characters", AuthState.signup_password, AuthState.set_signup_password, input_type="password"),
            width="100%", padding_top="1.1em",
        ),
        rx.box(
            auth_input("Confirm Password", "Re-enter your password", AuthState.signup_confirm_password, AuthState.set_signup_confirm_password, input_type="password"),
            width="100%", padding_top="1.1em",
        ),
        rx.cond(
            AuthState.signup_error != "",
            rx.box(
                rx.text(AuthState.signup_error, color=COLORS["danger"], size="2", font_family=FONT_BODY),
                padding_top="0.85em",
            ),
        ),
        rx.box(
            auth_button("Create Account", AuthState.sign_up),
            padding_top="1.6em",
            width="100%",
        ),
        rx.hstack(
            rx.text("Already have an account?", size="2", color=COLORS["slate"], font_family=FONT_BODY),
            rx.link(
                "Sign In",
                href="/signin",
                size="2",
                weight="bold",
                color=COLORS["primary"],
                font_family=FONT_BODY,
                _hover={"text_decoration": "underline"},
            ),
            spacing="2",
            justify="center",
            width="100%",
            padding_top="1.75em",
        ),
        width="100%",
        align_items="stretch",
    )


def signup_page() -> rx.Component:
    content = rx.cond(AuthState.signup_success, _success_view(), _form_view())
    return auth_card(content)