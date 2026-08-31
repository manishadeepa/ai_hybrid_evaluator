import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.components.auth.auth_card import auth_card
from ai_hybrid_evaluator.components.auth.auth_header import auth_header
from ai_hybrid_evaluator.components.auth.auth_input import auth_input
from ai_hybrid_evaluator.components.auth.auth_button import auth_button
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def login_page() -> rx.Component:
    content = rx.vstack(
        auth_header(
            "Welcome back",
            "Sign in to access the GenAI Hybrid Evaluator Administration Portal.",
        ),
        auth_input(
            "Official Email",
            "Enter your official email",
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
            rx.spacer(),
            rx.link(
                "Forgot Password?",
                href="#",
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["primary"],
                _hover={"text_decoration": "underline"},
            ),
            width="100%",
            padding_top="0.6em",
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
        rx.hstack(
            rx.text("Don't have an account?", size="2", color=COLORS["slate"], font_family=FONT_BODY),
            rx.link(
                "Create Account",
                href="/signup",
                size="2",
                weight="bold",
                color=COLORS["primary"],
                font_family=FONT_BODY,
                _hover={"text_decoration": "underline"},
            ),
            spacing="2",
            justify="center",
            width="100%",
            padding_top="1.4em",
        ),
        width="100%",
        align_items="stretch",
    )
    return auth_card(content)