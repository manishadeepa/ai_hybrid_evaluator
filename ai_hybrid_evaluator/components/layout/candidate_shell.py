"""Shared shell for Candidate pages — unified top bar + clean white sidebar + content area."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.topbar import unified_topbar
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def _candidate_nav_link(label: str, route: str, icon: str, active: bool) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.box(
                rx.icon(
                    icon,
                    size=16,
                    color=COLORS["primary"] if active else COLORS["slate"],
                ),
                background="#EDE9FE" if active else "transparent",
                padding="0.35em",
                border_radius="6px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text(
                label,
                color=COLORS["primary"] if active else "#334155",
                font_family=FONT_BODY,
                size="2",
                weight="bold" if active else "medium",
            ),
            spacing="3",
            align_items="center",
            width="100%",
            padding="0.55em 0.85em",
            background=COLORS["primary_soft"] if active else "transparent",
            border_radius="10px",
            transition="all 0.15s ease",
            _hover={"background": COLORS["primary_soft"] if active else "#F8FAFC"},
        ),
        href=route,
        width="100%",
        text_decoration="none",
        border_radius="10px",
    )


def candidate_sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            _candidate_nav_link("My Assessments", "/candidate/dashboard", "layout-grid", active == "assessments"),
            _candidate_nav_link("Profile", "/candidate/profile", "user", active == "profile"),
            rx.spacer(),
            # Logout
            rx.box(
                rx.hstack(
                    rx.icon("log-out", size=16, color=COLORS["slate"]),
                    rx.text(
                        "Logout",
                        color="#334155",
                        font_family=FONT_BODY,
                        size="2",
                        weight="medium",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="10px",
                padding="0.7em 1em",
                cursor="pointer",
                width="100%",
                on_click=AuthState.candidate_logout,
                _hover={"background": "#F8FAFC", "border_color": "#D0D5DD"},
                transition="all 0.15s ease",
            ),
            spacing="2",
            width="100%",
            height="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border_right=f"1px solid {COLORS['line']}",
        width="240px",
        min_width="240px",
        height="calc(100vh - 64px)",
        padding="1.5em 1em",
        display="flex",
        flex_direction="column",
    )


def candidate_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    return rx.vstack(
        # Unified Header
        unified_topbar(
            user_name="Candidate",
            role_name="Candidate",
            avatar_initial="C",
        ),
        # Body: Sidebar + Main Content Area
        rx.hstack(
            candidate_sidebar(active),
            rx.box(
                content,
                padding="2em",
                width="100%",
                height="calc(100vh - 64px)",
                overflow_y="auto",
                background=COLORS["canvas"],
            ),
            spacing="0",
            width="100%",
            flex="1",
            overflow="hidden",
        ),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        background=COLORS["canvas"],
    )
