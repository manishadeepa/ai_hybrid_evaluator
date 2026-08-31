"""Sidebar navigation — Dashboard, Users (Facilitators/Candidates), Assessments, Reports, Settings, Logout."""

import reflex as rx
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY

SIDEBAR_MUTED = "#94A3C4"
SIDEBAR_HOVER = "#232B45"


def nav_link(label: str, route: str, icon: str, active: bool, indent: bool = False) -> rx.Component:
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
            padding_left="2.4em" if indent else "0.8em",
            background=COLORS["primary"] if active else "transparent",
            border_radius="8px",
        ),
        href=route,
        width="100%",
        text_decoration="none",
        _hover={"background": "transparent" if active else SIDEBAR_HOVER},
        border_radius="8px",
    )


def users_menu_header(active: bool) -> rx.Component:
    return rx.hstack(
        rx.icon("users", size=16, color="white" if active else SIDEBAR_MUTED),
        rx.text("Users", color="white" if active else SIDEBAR_MUTED, font_family=FONT_BODY, size="2"),
        rx.spacer(),
        rx.icon(
            rx.cond(AdminState.users_menu_open, "chevron-down", "chevron-right"),
            size=14,
            color=SIDEBAR_MUTED,
        ),
        spacing="3",
        align_items="center",
        width="100%",
        padding="0.55em 0.8em",
        border_radius="8px",
        cursor="pointer",
        on_click=AdminState.toggle_users_menu,
        _hover={"background": SIDEBAR_HOVER},
    )


def logout_item() -> rx.Component:
    return rx.hstack(
        rx.icon("log-out", size=16, color=SIDEBAR_MUTED),
        rx.text("Logout", color=SIDEBAR_MUTED, font_family=FONT_BODY, size="2"),
        spacing="3",
        align_items="center",
        width="100%",
        padding="0.55em 0.8em",
        border_radius="8px",
        cursor="pointer",
        on_click=AuthState.logout,
        _hover={"background": SIDEBAR_HOVER},
    )


def sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(src="/tvs_logo.png", width="26px", height="26px", object_fit="contain"),
                rx.text("GenAI Hybrid Evaluator", font_family=FONT_BODY, weight="bold", size="2", color="white"),
                spacing="2",
                align_items="center",
                padding_bottom="1.8em",
            ),
            nav_link("Dashboard", "/admin/dashboard", "layout-dashboard", active == "dashboard"),
            users_menu_header(active in ("facilitators", "candidates")),
            rx.cond(
                AdminState.users_menu_open,
                rx.vstack(
                    nav_link("Facilitators", "/admin/facilitators", "user-cog", active == "facilitators", indent=True),
                    nav_link("Candidates", "/admin/candidates", "user", active == "candidates", indent=True),
                    spacing="1",
                    width="100%",
                ),
            ),
            nav_link("Assessments", "/admin/assessments", "file-text", active == "assessments"),
            nav_link("Reports", "/admin/reports", "bar-chart-3", active == "reports"),
            nav_link("Settings", "/admin/settings", "settings", active == "settings"),
            rx.spacer(),
            logout_item(),
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