"""
Clean White Sidebar navigation for Admin — Dashboard, Users (Facilitators/Candidates), Assessments, Reports, Settings, Logout.
Matches reference design with purple active states, clean outline icons, and subtle borders.
"""

import reflex as rx
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def nav_link(label: str, route: str, icon: str, active: bool, indent: bool = False) -> rx.Component:
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
            padding_left="2.2em" if indent else "0.85em",
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


def users_menu_header(active: bool) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("users", size=16, color=COLORS["slate"]),
            padding="0.35em",
            border_radius="6px",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.text(
            "Users",
            color="#334155",
            font_family=FONT_BODY,
            size="2",
            weight="medium",
        ),
        rx.spacer(),
        rx.icon(
            rx.cond(AdminState.users_menu_open, "chevron-up", "chevron-down"),
            size=14,
            color=COLORS["slate"],
        ),
        spacing="3",
        align_items="center",
        width="100%",
        padding="0.55em 0.85em",
        border_radius="10px",
        cursor="pointer",
        on_click=AdminState.toggle_users_menu,
        _hover={"background": "#F8FAFC"},
        transition="all 0.15s ease",
    )


def logout_item() -> rx.Component:
    return rx.box(
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
        on_click=AuthState.logout,
        _hover={"background": "#F8FAFC", "border_color": "#D0D5DD"},
        transition="all 0.15s ease",
    )


def sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            nav_link("Dashboard", "/admin/dashboard", "layout-grid", active == "dashboard"),
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
            nav_link("Assessments", "/admin/assessments", "clipboard-list", active == "assessments"),
            nav_link("Reports", "/admin/reports", "bar-chart-2", active == "reports"),
            nav_link("Settings", "/admin/settings", "settings", active == "settings"),
            rx.spacer(),
            logout_item(),
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