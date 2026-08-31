"""Shared candidate shell — sidebar + topbar + content area.
Mirrors the same pattern as admin_shell / facilitator_shell.
"""

import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY

SIDEBAR_MUTED = "#94A3C4"
SIDEBAR_HOVER = "#232B45"


def _candidate_nav_link(label: str, route: str, icon: str, active: bool) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=16, color="white" if active else SIDEBAR_MUTED),
            rx.text(
                label,
                color="white" if active else SIDEBAR_MUTED,
                font_family=FONT_BODY,
                size="2",
                weight="bold" if active else "regular",
            ),
            spacing="3",
            align_items="center",
            width="100%",
            padding="0.55em 0.8em",
            background=COLORS["primary"] if active else "transparent",
            border_radius="8px",
        ),
        href=route,
        width="100%",
        text_decoration="none",
        _hover={"background": "transparent" if active else SIDEBAR_HOVER},
        border_radius="8px",
    )


def candidate_sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            # Brand
            rx.hstack(
                rx.image(src="/tvs_logo.png", width="26px", height="26px", object_fit="contain"),
                rx.text("GenAI Hybrid Evaluator", font_family=FONT_BODY, weight="bold", size="2", color="white"),
                spacing="2",
                align_items="center",
                padding_bottom="1.8em",
            ),
            # Nav items
            _candidate_nav_link("My Assessments", "/candidate/dashboard", "clipboard-list", active == "assessments"),
            _candidate_nav_link("Profile", "/candidate/profile", "user", active == "profile"),
            rx.spacer(),
            # Logout
            rx.hstack(
                rx.icon("log-out", size=16, color=SIDEBAR_MUTED),
                rx.text("Logout", color=SIDEBAR_MUTED, font_family=FONT_BODY, size="2"),
                spacing="3",
                align_items="center",
                width="100%",
                padding="0.55em 0.8em",
                border_radius="8px",
                cursor="pointer",
                on_click=AuthState.candidate_logout,
                _hover={"background": SIDEBAR_HOVER},
            ),
            spacing="1",
            width="100%",
            height="100%",
            align_items="stretch",
        ),
        background=COLORS["ink"],
        width="240px",
        min_width="240px",
        height="100vh",
        padding="1.5em 1em",
    )


def candidate_topbar(title: str, subtitle: str) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="5", weight="bold", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.text(subtitle, size="2", color=COLORS["slate"], font_family=FONT_BODY),
            spacing="0",
            align_items="start",
        ),
        rx.spacer(),
        rx.hstack(
            rx.box(
                rx.icon("user", size=14, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="0.35em",
                border_radius="50%",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(
                    "Welcome, " + AuthState.candidate_name,
                    font_family=FONT_BODY,
                    size="2",
                    weight="medium",
                    color=COLORS["ink"],
                ),
                rx.text(
                    AuthState.candidate_emp_id,
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="0",
                align_items="start",
            ),
            spacing="2",
            align_items="center",
        ),
        width="100%",
        padding="1.4em 2em",
        border_bottom=f"1px solid {COLORS['line']}",
        background=COLORS["surface"],
        align_items="center",
    )


def candidate_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    return rx.hstack(
        candidate_sidebar(active),
        rx.vstack(
            candidate_topbar(title, subtitle),
            rx.box(content, padding="2em", width="100%"),
            spacing="0",
            width="100%",
            height="100vh",
            overflow_y="auto",
            background=COLORS["canvas"],
        ),
        spacing="0",
        width="100%",
        height="100vh",
    )
