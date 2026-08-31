"""Shared shell for every Facilitator page — sidebar + top bar + content area."""

import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY

SIDEBAR_MUTED = "#94A3C4"
SIDEBAR_HOVER = "#232B45"


def nav_link(label: str, route: str, icon: str, active: bool) -> rx.Component:
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
            background="#0E9F6E" if active else "transparent",
            border_radius="8px",
        ),
        href=route,
        width="100%",
        text_decoration="none",
        _hover={"background": "transparent" if active else SIDEBAR_HOVER},
        border_radius="8px",
    )


def sidebar_test_sublink(assessment_name: str, test_name: str, is_final: bool) -> rx.Component:
    is_active = (FacilitatorState.selected_assessment_name == assessment_name) & (FacilitatorState.selected_test_name == test_name)
    has_qp = FacilitatorState.question_papers.get(assessment_name, {}).contains(test_name)
    return rx.hstack(
        rx.cond(
            is_final,
            rx.icon("award", size=11, color=rx.cond(is_active, "#FDE68A", "#FCD34D")),
            rx.icon("file-text", size=11, color=rx.cond(is_active, "white", "#A7F3D0")),
        ),
        rx.text(
            test_name,
            font_family=FONT_BODY,
            size="1",
            color=rx.cond(is_active, "white", "#D1FAE5"),
            weight=rx.cond(is_active, "bold", "regular"),
            no_of_lines=1,
            overflow="hidden",
            text_overflow="ellipsis",
            flex="1",
        ),
        rx.cond(
            has_qp,
            rx.box(width="5px", height="5px", border_radius="50%", background="#34D399"),
            rx.box(width="5px", height="5px", border_radius="50%", background="#FBBF24"),
        ),
        spacing="2",
        align_items="center",
        padding="0.25em 0.6em 0.25em 2.2em",
        border_radius="4px",
        cursor="pointer",
        width="100%",
        background=rx.cond(
            is_active,
            rx.cond(is_final, "#78350F", "#047857"),
            "transparent",
        ),
        on_click=FacilitatorState.open_assessment_test(assessment_name, test_name),
        _hover={"background": rx.cond(is_final, "#92400E", "#065F46")},
    )


def sidebar_approved_assessment_item(a: dict) -> rx.Component:
    is_sel = FacilitatorState.selected_assessment_name == a["name"]
    return rx.vstack(
        rx.hstack(
            rx.icon("file-check-2", size=13, color=rx.cond(is_sel, "white", "#6EE7B7")),
            rx.text(
                a["name"],
                font_family=FONT_BODY,
                size="1",
                weight=rx.cond(is_sel, "bold", "medium"),
                color=rx.cond(is_sel, "white", "#6EE7B7"),
                no_of_lines=1,
                overflow="hidden",
                text_overflow="ellipsis",
                max_width="145px",
            ),
            rx.spacer(),
            rx.icon(
                rx.cond(is_sel, "chevron-down", "chevron-right"),
                size=12,
                color=rx.cond(is_sel, "white", "#6EE7B7"),
            ),
            spacing="2",
            align_items="center",
            width="100%",
            padding="0.4em 0.8em 0.4em 1.6em",
            border_radius="6px",
            cursor="pointer",
            background=rx.cond(is_sel, "#059669", "transparent"),
            on_click=FacilitatorState.open_assessment_by_name(a["name"]),
            _hover={"background": "#064E3B"},
        ),
        # Test-wise sub-links
        rx.cond(
            is_sel,
            rx.vstack(
                rx.foreach(
                    a["tests"],
                    lambda t: sidebar_test_sublink(a["name"], t, False),
                ),
                sidebar_test_sublink(a["name"], a["final_test"], True),
                spacing="1",
                width="100%",
                padding_top="0.1em",
                padding_bottom="0.2em",
            ),
        ),
        spacing="0",
        width="100%",
    )


def facilitator_sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(src="/tvs_logo.png", width="26px", height="26px", object_fit="contain"),
                rx.text("GenAI Hybrid Evaluator", font_family=FONT_BODY, weight="bold", size="2", color="white"),
                spacing="2",
                align_items="center",
                padding_bottom="1.8em",
            ),
            nav_link("My Assessments", "/facilitator/dashboard", "clipboard-list", active == "assessments"),
            # ── Approved assessment quick-links with test sub-items ───────
            rx.cond(
                FacilitatorState.approved_assessments.length() > 0,
                rx.vstack(
                    rx.foreach(
                        FacilitatorState.approved_assessments,
                        sidebar_approved_assessment_item,
                    ),
                    spacing="0",
                    width="100%",
                    align_items="stretch",
                    padding_top="0.3em",
                ),
            ),
            nav_link("Profile", "/facilitator/profile", "user", active == "profile"),
            rx.spacer(),
            rx.hstack(
                rx.icon("log-out", size=16, color=SIDEBAR_MUTED),
                rx.text("Logout", color=SIDEBAR_MUTED, font_family=FONT_BODY, size="2"),
                spacing="3",
                align_items="center",
                width="100%",
                padding="0.55em 0.8em",
                border_radius="8px",
                cursor="pointer",
                on_click=AuthState.facilitator_logout,
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


def facilitator_topbar(title: str, subtitle: str) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="5", weight="bold", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.text(subtitle, size="2", color=COLORS["slate"], font_family=FONT_BODY),
            spacing="0",
            align_items="start",
        ),
        rx.spacer(),
        rx.text(
            "Welcome, " + AuthState.facilitator_name,
            font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"],
        ),
        width="100%",
        padding="1.4em 2em",
        border_bottom=f"1px solid {COLORS['line']}",
        background=COLORS["surface"],
        align_items="center",
    )


def facilitator_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    return rx.hstack(
        facilitator_sidebar(active),
        rx.vstack(
            facilitator_topbar(title, subtitle),
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