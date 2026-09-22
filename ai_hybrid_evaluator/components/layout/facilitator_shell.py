"""Shared shell for Facilitator pages — unified top bar + clean white sidebar + content area."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.topbar import unified_topbar
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def nav_link(label: str, route: str, icon: str, active: bool) -> rx.Component:
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


def sidebar_test_sublink(assessment_name: str, test_name: str, is_final: bool) -> rx.Component:
    is_active = (FacilitatorState.selected_assessment_name == assessment_name) & (FacilitatorState.selected_test_name == test_name)
    has_qp = FacilitatorState.question_papers.get(assessment_name, {}).contains(test_name)
    return rx.hstack(
        rx.text(
            test_name,
            font_family=FONT_BODY,
            size="1",
            color=rx.cond(is_active, COLORS["primary"], "#475467"),
            weight=rx.cond(is_active, "bold", "medium"),
            no_of_lines=1,
            overflow="hidden",
            text_overflow="ellipsis",
            flex="1",
        ),
        rx.cond(
            has_qp,
            rx.box(width="6px", height="6px", border_radius="50%", background="#10B981"),
            rx.cond(
                is_final,
                rx.box(width="7px", height="7px", border_radius="50%", border="1.5px solid #94A3B8", background="transparent"),
                rx.box(width="6px", height="6px", border_radius="50%", background="#F59E0B"),
            ),
        ),
        spacing="2",
        align_items="center",
        padding="0.32em 0.8em 0.32em 0.6em",
        border_radius="6px",
        cursor="pointer",
        width="100%",
        background=rx.cond(
            is_active,
            COLORS["primary_soft"],
            "transparent",
        ),
        on_click=FacilitatorState.open_assessment_test(assessment_name, test_name),
        _hover={"background": rx.cond(is_active, COLORS["primary_soft"], "#F8FAFC")},
        transition="all 0.15s ease",
    )


def workspace_subnav_item(label: str, icon: str, tab_key: str, assessment_name: str) -> rx.Component:
    """A sidebar sub-navigation item that sets the active workspace tab."""
    is_tab_active = (
        (FacilitatorState.selected_assessment_name == assessment_name)
        & (FacilitatorState.active_workspace_tab == tab_key)
    )
    return rx.hstack(
        rx.box(
            rx.icon(
                icon,
                size=14,
                color=rx.cond(is_tab_active, COLORS["primary"], COLORS["slate"]),
            ),
            background=rx.cond(is_tab_active, "#EDE9FE", "transparent"),
            padding="0.28em",
            border_radius="5px",
            display="flex",
            align_items="center",
            justify_content="center",
            flex_shrink=0,
        ),
        rx.text(
            label,
            font_family=FONT_BODY,
            size="2",
            color=rx.cond(is_tab_active, COLORS["primary"], "#334155"),
            weight=rx.cond(is_tab_active, "bold", "medium"),
        ),
        spacing="2",
        align_items="center",
        width="100%",
        padding="0.45em 0.8em 0.45em 1.6em",
        border_radius="8px",
        cursor="pointer",
        background=rx.cond(is_tab_active, COLORS["primary_soft"], "transparent"),
        on_click=FacilitatorState.open_assessment_tab(assessment_name, tab_key),
        _hover={"background": rx.cond(is_tab_active, COLORS["primary_soft"], "#F8FAFC")},
        transition="all 0.15s ease",
    )


def sidebar_approved_assessment_item(a: dict) -> rx.Component:
    is_sel = FacilitatorState.selected_assessment_name == a["name"]
    is_tests_active = (
        (FacilitatorState.selected_assessment_name == a["name"])
        & (FacilitatorState.active_workspace_tab == "tests")
    )
    return rx.vstack(
        # Assessment header row
        rx.hstack(
            rx.icon("clipboard-check", size=14, color=rx.cond(is_sel, COLORS["primary"], COLORS["slate"])),
            rx.text(
                a["name"],
                font_family=FONT_BODY,
                size="1",
                weight=rx.cond(is_sel, "bold", "semibold"),
                color=rx.cond(is_sel, COLORS["primary"], "#1E293B"),
                no_of_lines=1,
                overflow="hidden",
                text_overflow="ellipsis",
                max_width="145px",
            ),
            rx.spacer(),
            rx.icon(
                rx.cond(is_sel, "chevron-down", "chevron-right"),
                size=12,
                color=COLORS["slate"],
            ),
            spacing="2",
            align_items="center",
            width="100%",
            padding="0.45em 0.8em 0.45em 1.2em",
            border_radius="8px",
            cursor="pointer",
            background=rx.cond(is_sel, "#F5F3FF", "transparent"),
            on_click=FacilitatorState.open_assessment_by_name(a["name"]),
            _hover={"background": "#F8FAFC"},
            transition="all 0.15s ease",
        ),
        # Workspace sub-navigation (shown when assessment is selected)
        rx.cond(
            is_sel,
            rx.vstack(
                # Tests row (with nested test sub-items when active)
                rx.vstack(
                    # Tests nav item
                    rx.hstack(
                        rx.box(
                            rx.icon(
                                "file-spreadsheet",
                                size=14,
                                color=rx.cond(is_tests_active, COLORS["primary"], COLORS["slate"]),
                            ),
                            background=rx.cond(is_tests_active, "#EDE9FE", "transparent"),
                            padding="0.28em",
                            border_radius="5px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            flex_shrink=0,
                        ),
                        rx.text(
                            "Tests",
                            font_family=FONT_BODY,
                            size="2",
                            color=rx.cond(is_tests_active, COLORS["primary"], "#334155"),
                            weight=rx.cond(is_tests_active, "bold", "medium"),
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                        padding="0.45em 0.8em 0.45em 1.6em",
                        border_radius="8px",
                        cursor="pointer",
                        background=rx.cond(is_tests_active, COLORS["primary_soft"], "transparent"),
                        on_click=FacilitatorState.open_assessment_tab(a["name"], "tests"),
                        _hover={"background": rx.cond(is_tests_active, COLORS["primary_soft"], "#F8FAFC")},
                        transition="all 0.15s ease",
                    ),
                    # Nested test sub-links in a tree column with left border
                    rx.box(
                        rx.vstack(
                            rx.foreach(
                                a["tests"],
                                lambda t: sidebar_test_sublink(a["name"], t, False),
                            ),
                            rx.cond(
                                a["final_test"] != "",
                                sidebar_test_sublink(a["name"], a["final_test"], True),
                            ),
                            spacing="0",
                            width="100%",
                        ),
                        border_left="1.5px solid #E2E8F0",
                        margin_left="2.3em",
                        padding_left="0.4em",
                        margin_y="0.1em",
                        width="calc(100% - 2.3em)",
                    ),
                    spacing="0",
                    width="100%",
                ),
                # Evaluation
                workspace_subnav_item("Evaluation", "pencil-line", "evaluation", a["name"]),
                # Weightage
                workspace_subnav_item("Weightage", "sliders-horizontal", "weightage", a["name"]),
                # Results
                workspace_subnav_item("Results", "bar-chart-2", "results", a["name"]),
                spacing="1",
                width="100%",
                padding_top="0.1em",
                padding_bottom="0.3em",
            ),
        ),
        spacing="0",
        width="100%",
    )


def facilitator_sidebar(active: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            nav_link("My Assessments", "/facilitator/dashboard", "layout-grid", active == "assessments"),
            # ── Approved assessment quick-links with test sub-items ───────
            rx.cond(
                FacilitatorState.approved_assessments.length() > 0,
                rx.vstack(
                    rx.text(
                        "ACTIVE WORKSPACES",
                        font_family=FONT_BODY,
                        size="1",
                        weight="bold",
                        color=COLORS["slate"],
                        letter_spacing="0.05em",
                        padding_left="0.85em",
                        padding_top="0.6em",
                    ),
                    rx.foreach(
                        FacilitatorState.approved_assessments,
                        sidebar_approved_assessment_item,
                    ),
                    spacing="1",
                    width="100%",
                    align_items="stretch",
                ),
            ),
            nav_link("Feedback", "/facilitator/feedback", "message-square", active == "feedback"),
            nav_link("Profile", "/facilitator/profile", "user", active == "profile"),
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
                on_click=AuthState.facilitator_logout,
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


def facilitator_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    display_name = rx.cond(
        AuthState.facilitator_name != "",
        AuthState.facilitator_name,
        "Facilitator",
    )
    display_initial = rx.cond(
        AuthState.facilitator_name != "",
        AuthState.facilitator_name[0],
        "F",
    )
    return rx.vstack(
        # Unified Header
        unified_topbar(
            user_name=display_name,
            role_name="Facilitator",
            avatar_initial=display_initial,
        ),
        # Body: Sidebar + Main Content Area
        rx.hstack(
            facilitator_sidebar(active),
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