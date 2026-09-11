"""
Candidate sign-in — login using Candidate / Employee ID and password created by the Admin.
Matches the standard Auth layout used by Admin and Facilitator sign-in portals.
"""

import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.components.auth.auth_card import auth_card
from ai_hybrid_evaluator.components.auth.auth_header import auth_header
from ai_hybrid_evaluator.components.auth.auth_input import auth_input
from ai_hybrid_evaluator.components.auth.auth_button import auth_button
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def candidate_login_page() -> rx.Component:
    content = rx.vstack(
        auth_header(
            "Candidate Sign In",
            "Sign in with your Employee ID and the password provided by your Administrator to access your examination.",
        ),
        auth_input(
            "Employee ID",
            "e.g. CAND-2031",
            AuthState.candidate_signin_id,
            AuthState.set_candidate_signin_id,
            on_key_down=AuthState.handle_candidate_keydown,
        ),
        auth_input(
            "Password",
            "Enter the password provided by Admin",
            AuthState.candidate_signin_password,
            AuthState.set_candidate_signin_password,
            input_type="password",
            on_key_down=AuthState.handle_candidate_keydown,
        ),
        rx.cond(
            AuthState.candidate_signin_error != "",
            rx.box(
                rx.hstack(
                    rx.icon("circle-alert", size=16, color=COLORS["danger"]),
                    rx.text(
                        AuthState.candidate_signin_error,
                        color=COLORS["danger"],
                        size="2",
                        font_family=FONT_BODY,
                    ),
                    spacing="2",
                    align_items="center",
                ),
                background="#FEF3F2",
                border="1px solid #FDA29B",
                border_radius="8px",
                padding="0.65em 0.85em",
                margin_top="0.6em",
                width="100%",
            ),
        ),
        rx.box(
            auth_button("Sign In", AuthState.candidate_sign_in),
            padding_top="1.4em",
            width="100%",
        ),
        spacing="3",
        width="100%",
        align_items="stretch",
    )
    return auth_card(content)
