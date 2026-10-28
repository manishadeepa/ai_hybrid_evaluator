"""
Candidate Dashboard — Gen AI Hybrid Evaluator
Matches the enterprise candidate dashboard reference layout:
- Welcome banner with candidate name, lavender-blue gradient, and decorative illustrations
- Statistics & Donut Charts row:
    * Total Assessments card (interactive, opens All My Assessments popup)
    * Test Completion (with assessment selector, interactive donut segments and legend items)
    * Result Status (with assessment selector, interactive donut segments and legend items)
- Assessment Summary full-width table with View Tests action
- Recent Activity vertical timeline at the bottom
- Interactive Popups:
    1. All My Assessments
    2. Completed Tests
    3. Not Completed Tests
    4. Evaluated Tests
    5. Pending Evaluation
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.candidate_shell import candidate_shell
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.candidate_state import CandidateState, CandidateProfileState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────────────────────
# 1. Welcome Banner Decorative SVG Illustrations
# ─────────────────────────────────────────────────────────────────────────────

def _banner_student_svg() -> rx.Component:
    """Vector illustration of student with laptop."""
    return rx.el.svg(
        rx.el.circle(cx="60", cy="55", r="42", fill="#EDE9FE", opacity="0.6"),
        rx.el.path(
            d="M 38 42 C 34 25, 48 12, 65 14 C 78 15, 86 28, 84 44 C 84 56, 88 64, 86 72 C 84 80, 78 84, 76 84 C 74 84, 76 74, 74 65 C 72 56, 68 54, 64 54 Z",
            fill="#1E1B4B",
        ),
        rx.el.path(
            d="M 44 80 C 44 68, 54 62, 64 62 C 74 62, 84 68, 84 80 L 88 100 L 38 100 Z",
            fill="#7C3AED",
        ),
        rx.el.path(d="M 59 56 L 67 56 L 67 65 L 59 65 Z", fill="#FCD34D"),
        rx.el.path(
            d="M 52 35 C 52 25, 72 25, 72 35 C 72 48, 52 48, 52 35 Z",
            fill="#FDE68A",
        ),
        rx.el.path(
            d="M 48 30 C 54 20, 72 20, 76 30 C 74 34, 68 32, 64 34 C 58 36, 52 38, 48 30 Z",
            fill="#1E1B4B",
        ),
        rx.el.path(d="M 72 74 L 88 74 L 92 88 L 68 88 Z", fill="#1E293B"),
        rx.el.path(d="M 70 88 L 96 88 L 98 92 L 66 92 Z", fill="#334155"),
        rx.el.path(d="M 73 76 L 87 76 L 90 86 L 70 86 Z", fill="#818CF8", opacity="0.85"),
        view_box="0 0 120 105",
        width="110",
        height="96",
        xmlns="http://www.w3.org/2000/svg",
        style={"display": "block", "flexShrink": "0"},
    )


def _banner_target_svg() -> rx.Component:
    """Target board with bullseye arrow and floating assessment paper illustration."""
    return rx.el.svg(
        rx.el.rect(
            x="20",
            y="12",
            width="80",
            height="86",
            rx="12",
            fill="#FFFFFF",
            stroke="#E0E7FF",
            stroke_width="2",
            opacity="0.9",
        ),
        rx.el.circle(cx="34", cy="28", r="3", fill="#C7D2FE"),
        rx.el.line(x1="44", y1="28", x2="82", y2="28", stroke="#E0E7FF", stroke_width="3", stroke_linecap="round"),
        rx.el.circle(cx="34", cy="42", r="3", fill="#C7D2FE"),
        rx.el.line(x1="44", y1="42", x2="74", y2="42", stroke="#E0E7FF", stroke_width="3", stroke_linecap="round"),
        rx.el.circle(cx="34", cy="56", r="3", fill="#C7D2FE"),
        rx.el.line(x1="44", y1="56", x2="68", y2="56", stroke="#E0E7FF", stroke_width="3", stroke_linecap="round"),
        rx.el.circle(cx="100", cy="54", r="34", fill="#EDE9FE", stroke="#DDD6FE", stroke_width="1.5"),
        rx.el.circle(cx="100", cy="54", r="26", fill="#FFFFFF", stroke="#C4B5FD", stroke_width="2"),
        rx.el.circle(cx="100", cy="54", r="18", fill="#EDE9FE", stroke="#8B5CF6", stroke_width="3"),
        rx.el.circle(cx="100", cy="54", r="10", fill="#7C3AED"),
        rx.el.circle(cx="100", cy="54", r="4", fill="#FFFFFF"),
        rx.el.line(x1="126", y1="28", x2="98", y2="56", stroke="#7C3AED", stroke_width="3.5", stroke_linecap="round"),
        rx.el.path(d="M 126 28 L 132 26 L 130 32 Z", fill="#8B5CF6"),
        rx.el.path(d="M 124 30 L 128 36 L 122 34 Z", fill="#8B5CF6"),
        rx.el.path(d="M 16 28 Q 16 34 10 34 Q 16 34 16 40 Q 16 34 22 34 Q 16 34 16 28 Z", fill="#C4B5FD"),
        rx.el.path(d="M 134 76 Q 134 80 130 80 Q 134 80 134 84 Q 134 80 138 80 Q 134 80 134 76 Z", fill="#A78BFA"),
        view_box="0 0 150 105",
        width="140",
        height="98",
        xmlns="http://www.w3.org/2000/svg",
        style={"display": "block", "flexShrink": "0"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Welcome Banner
# ─────────────────────────────────────────────────────────────────────────────

def _welcome_banner() -> rx.Component:
    cand_name = rx.cond(
        AuthState.candidate_name != "",
        AuthState.candidate_name,
        rx.cond(
            CandidateProfileState.full_name != "",
            CandidateProfileState.full_name,
            "Candidate",
        ),
    )

    return rx.box(
        rx.hstack(
            rx.hstack(
                _banner_student_svg(),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Welcome, ",
                            font_family=FONT_DISPLAY,
                            size="6",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            cand_name,
                            rx.text("!", as_="span", color=COLORS["ink"]),
                            font_family=FONT_DISPLAY,
                            size="6",
                            weight="bold",
                            color="#7C3AED",
                        ),
                        spacing="1",
                        align_items="center",
                        flex_wrap="wrap",
                    ),
                    rx.text(
                        "Track your assessments, view your progress and check your results.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="1",
                    align_items="start",
                    justify_content="center",
                ),
                spacing="3",
                align_items="center",
            ),
            rx.spacer(),
            rx.box(
                _banner_target_svg(),
                display=["none", "none", "block"],
            ),
            width="100%",
            align_items="center",
            padding="1.2em 1.6em",
        ),
        background="linear-gradient(135deg, #F5F3FF 0%, #EEF2FF 50%, #F0F9FF 100%)",
        border="1px solid #E0E7FF",
        border_radius="16px",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        width="100%",
        overflow="hidden",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Donut Slice SVG Renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_interactive_donut_slice(seg: dict) -> rx.Component:
    """Clickable donut slice that triggers category-specific popup modal.

    We MUST NOT call an event handler with a dynamic Var argument inside
    rx.foreach — that generates broken JS and crashes React Router's
    useContext call.  Instead, use rx.cond chains to pick a static handler.
    """
    return rx.cond(
        seg["d"] == "",
        rx.fragment(),
        rx.cond(
            seg["name"] == "Completed",
            rx.el.path(
                d=seg["d"], fill=seg["fill"],
                stroke="#ffffff", stroke_width="2", cursor="pointer",
                on_click=CandidateState.open_completed_tests_modal,
                _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
                transition="all 0.15s ease",
            ),
            rx.cond(
                seg["name"] == "Not Completed",
                rx.el.path(
                    d=seg["d"], fill=seg["fill"],
                    stroke="#ffffff", stroke_width="2", cursor="pointer",
                    on_click=CandidateState.open_not_completed_tests_modal,
                    _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
                    transition="all 0.15s ease",
                ),
                rx.cond(
                    seg["name"] == "Evaluated",
                    rx.el.path(
                        d=seg["d"], fill=seg["fill"],
                        stroke="#ffffff", stroke_width="2", cursor="pointer",
                        on_click=CandidateState.open_evaluated_tests_modal,
                        _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
                        transition="all 0.15s ease",
                    ),
                    rx.cond(
                        seg["name"] == "Pending Evaluation",
                        rx.el.path(
                            d=seg["d"], fill=seg["fill"],
                            stroke="#ffffff", stroke_width="2", cursor="pointer",
                            on_click=CandidateState.open_pending_evaluation_modal,
                            _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
                            transition="all 0.15s ease",
                        ),
                        # Empty segment (fallback — no click)
                        rx.el.path(
                            d=seg["d"], fill=seg["fill"],
                            stroke="#ffffff", stroke_width="2",
                        ),
                    ),
                ),
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Statistics and Donut Charts Row (3 cards in 1 row)
# ─────────────────────────────────────────────────────────────────────────────

def _card_total_assessments() -> rx.Component:
    """Card 1: Total Assessments card — clickable to open All My Assessments modal."""
    return rx.box(
        rx.vstack(
            # Top row: heading like Test status in black font + chevron
            rx.hstack(
                rx.text(
                    "Total Assessments",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.spacer(),
                rx.box(
                    rx.icon("chevron-right", size=16, color="#7C3AED"),
                    background="#F5F3FF",
                    padding="0.35em",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    _hover={"background": "#EDE9FE", "transform": "translateX(2px)"},
                    transition="all 0.15s ease",
                ),
                width="100%",
                align_items="center",
            ),
            # Center of the box: count in the center
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("file-text", size=22, color="#7C3AED"),
                        background="#F5F3FF",
                        padding="0.5em",
                        border_radius="10px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        flex_shrink="0",
                    ),
                    rx.text(
                        CandidateState.dashboard_total_assessments.to_string(),
                        font_family=FONT_DISPLAY,
                        size="8",
                        weight="bold",
                        color=COLORS["ink"],
                        line_height="1",
                    ),
                    spacing="3",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(
                    "Assigned to you",
                    font_family=FONT_BODY,
                    size="2",
                    weight="regular",
                    color="#64748B",
                ),
                spacing="1",
                align_items="center",
                justify_content="center",
                width="100%",
                height="100%",
                padding_y="0.6em",
            ),
            spacing="3",
            align_items="start",
            width="100%",
            height="100%",
        ),
        background="white",
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        height="100%",
        min_height="165px",
        cursor="pointer",
        on_click=CandidateState.open_all_assessments_modal,
        _hover={
            "border_color": "#C4B5FD",
            "box_shadow": "0 4px 14px rgba(124, 58, 237, 0.08)",
            "transform": "translateY(-1px)",
        },
        transition="all 0.18s ease",
    )


def _card_test_completion() -> rx.Component:
    """Card 2: Test Completion Donut Chart with shared Assessment Selector."""
    return rx.box(
        rx.vstack(
            # Header with Assessment Selector
            rx.hstack(
                rx.text(
                    "Test Completion",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.spacer(),
                rx.select(
                    CandidateState.assigned_assessment_names,
                    value=CandidateState.dashboard_selected_assessment,
                    on_change=CandidateState.set_dashboard_selected_assessment,
                    size="1",
                    radius="medium",
                    variant="surface",
                    min_width="90px",
                ),
                width="100%",
                align_items="center",
            ),
            # Body: Donut and Legend
            rx.hstack(
                # Donut Chart SVG
                rx.box(
                    rx.el.svg(
                        rx.el.g(
                            rx.foreach(
                                CandidateState.selected_completion_donut_segments,
                                _render_interactive_donut_slice,
                            ),
                            # Center Cutout Circle (non-clickable)
                            rx.el.circle(
                                cx="75",
                                cy="75",
                                r="42",
                                fill="#ffffff",
                                style={"pointerEvents": "none"},
                            ),
                            # Center Total Count
                            rx.el.text(
                                CandidateState.selected_total_tests.to_string(),
                                x="75",
                                y="69",
                                text_anchor="middle",
                                dominant_baseline="central",
                                fill="#0F172A",
                                font_size="22",
                                font_weight="700",
                                font_family="Plus Jakarta Sans, system-ui, sans-serif",
                                style={"pointerEvents": "none"},
                            ),
                            # Center Subtitle
                            rx.el.text(
                                "Total Tests",
                                x="75",
                                y="87",
                                text_anchor="middle",
                                dominant_baseline="central",
                                fill="#64748B",
                                font_size="10",
                                font_weight="500",
                                font_family="Inter, system-ui, sans-serif",
                                style={"pointerEvents": "none"},
                            ),
                        ),
                        view_box="0 0 150 150",
                        width="122",
                        height="122",
                        xmlns="http://www.w3.org/2000/svg",
                        style={"display": "block"},
                    ),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                # Legend on Right (Both labels/indicators clickable)
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            width="9px",
                            height="9px",
                            border_radius="50%",
                            background="#7C3AED",
                            flex_shrink="0",
                        ),
                        rx.text(
                            "Completed",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.spacer(),
                        rx.text(
                            CandidateState.selected_completed_tests.to_string(),
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        width="100%",
                        align_items="center",
                        spacing="2",
                        cursor="pointer",
                        padding="0.25em 0.4em",
                        border_radius="6px",
                        _hover={"background": "#F5F3FF"},
                        on_click=CandidateState.open_completed_tests_modal,
                        title="Click to view Completed Tests",
                    ),
                    rx.hstack(
                        rx.box(
                            width="9px",
                            height="9px",
                            border_radius="50%",
                            background="#DDD6FE",
                            flex_shrink="0",
                        ),
                        rx.text(
                            "Not Completed",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.spacer(),
                        rx.text(
                            CandidateState.selected_not_completed_tests.to_string(),
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        width="100%",
                        align_items="center",
                        spacing="2",
                        cursor="pointer",
                        padding="0.25em 0.4em",
                        border_radius="6px",
                        _hover={"background": "#F5F3FF"},
                        on_click=CandidateState.open_not_completed_tests_modal,
                        title="Click to view Not Completed Tests",
                    ),
                    spacing="2",
                    width="100%",
                    justify_content="center",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        background="white",
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        height="100%",
        min_height="165px",
    )


def _card_result_status() -> rx.Component:
    """Card 3: Result Status Donut Chart with shared Assessment Selector."""
    return rx.box(
        rx.vstack(
            # Header with Assessment Selector
            rx.hstack(
                rx.text(
                    "Result Status",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.spacer(),
                rx.select(
                    CandidateState.assigned_assessment_names,
                    value=CandidateState.dashboard_selected_assessment,
                    on_change=CandidateState.set_dashboard_selected_assessment,
                    size="1",
                    radius="medium",
                    variant="surface",
                    min_width="90px",
                ),
                width="100%",
                align_items="center",
            ),
            # Body: Donut and Legend
            rx.hstack(
                # Donut Chart SVG
                rx.box(
                    rx.el.svg(
                        rx.el.g(
                            rx.foreach(
                                CandidateState.selected_result_status_donut_segments,
                                _render_interactive_donut_slice,
                            ),
                            # Center Cutout Circle (non-clickable)
                            rx.el.circle(
                                cx="75",
                                cy="75",
                                r="42",
                                fill="#ffffff",
                                style={"pointerEvents": "none"},
                            ),
                            # Center Submitted Count
                            rx.el.text(
                                CandidateState.selected_submitted_tests.to_string(),
                                x="75",
                                y="69",
                                text_anchor="middle",
                                dominant_baseline="central",
                                fill="#0F172A",
                                font_size="22",
                                font_weight="700",
                                font_family="Plus Jakarta Sans, system-ui, sans-serif",
                                style={"pointerEvents": "none"},
                            ),
                            # Center Subtitle (matches screenshot: 'Submitted')
                            rx.el.text(
                                "Submitted",
                                x="75",
                                y="87",
                                text_anchor="middle",
                                dominant_baseline="central",
                                fill="#64748B",
                                font_size="10",
                                font_weight="500",
                                font_family="Inter, system-ui, sans-serif",
                                style={"pointerEvents": "none"},
                            ),
                        ),
                        view_box="0 0 150 150",
                        width="122",
                        height="122",
                        xmlns="http://www.w3.org/2000/svg",
                        style={"display": "block"},
                    ),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                # Legend on Right (Both labels/indicators clickable)
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            width="9px",
                            height="9px",
                            border_radius="50%",
                            background="#10B981",
                            flex_shrink="0",
                        ),
                        rx.text(
                            "Evaluated",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.spacer(),
                        rx.text(
                            CandidateState.selected_evaluated_tests.to_string(),
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        width="100%",
                        align_items="center",
                        spacing="2",
                        cursor="pointer",
                        padding="0.25em 0.4em",
                        border_radius="6px",
                        _hover={"background": "#F0FDF4"},
                        on_click=CandidateState.open_evaluated_tests_modal,
                        title="Click to view Evaluated Tests",
                    ),
                    rx.hstack(
                        rx.box(
                            width="9px",
                            height="9px",
                            border_radius="50%",
                            background="#F87171",
                            flex_shrink="0",
                        ),
                        rx.text(
                            "Pending Evaluation",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.spacer(),
                        rx.text(
                            CandidateState.selected_pending_evaluation_tests.to_string(),
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        width="100%",
                        align_items="center",
                        spacing="2",
                        cursor="pointer",
                        padding="0.25em 0.4em",
                        border_radius="6px",
                        _hover={"background": "#FEF2F2"},
                        on_click=CandidateState.open_pending_evaluation_modal,
                        title="Click to view Pending Evaluation Tests",
                    ),
                    spacing="2",
                    width="100%",
                    justify_content="center",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        background="white",
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        height="100%",
        min_height="165px",
    )


def _statistics_row() -> rx.Component:
    return rx.grid(
        _card_total_assessments(),
        _card_test_completion(),
        _card_result_status(),
        columns=rx.breakpoints(initial="1", md="3"),
        spacing="4",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Assessment Summary Table
# ─────────────────────────────────────────────────────────────────────────────

def _summary_table_row(item: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(
                item["name"],
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
                flex="2",
                text_align="left",
            ),
            rx.text(
                item["total_tests"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                flex="1",
                text_align="center",
            ),
            rx.text(
                item["completed_tests"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                flex="1",
                text_align="center",
            ),
            rx.text(
                item["not_completed_tests"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                flex="1",
                text_align="center",
            ),
            rx.box(
                rx.link(
                    rx.button(
                        "View Tests",
                        size="1",
                        background="#F3E8FF",
                        color="#7C3AED",
                        font_family=FONT_BODY,
                        font_weight="medium",
                        border_radius="6px",
                        padding="0.4em 0.85em",
                        cursor="pointer",
                        _hover={"background": "#EDE9FE", "color": "#6D28D9"},
                        transition="all 0.15s ease",
                    ),
                    href="/candidate/assessments",
                    text_decoration="none",
                ),
                flex="1",
                display="flex",
                justify_content="center",
            ),
            width="100%",
            align_items="center",
            padding="0.9em 1.2em",
        ),
        border_bottom=f"1px solid {COLORS['line']}",
        _hover={"background": "#FAFAFA"},
        transition="background 0.12s ease",
        width="100%",
    )


def _assessment_summary_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=18, color="#7C3AED"),
                    background="#F5F3FF",
                    padding="0.55em",
                    border_radius="8px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text(
                        "Assessment Summary",
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Your assigned assessments and progress.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
                padding_bottom="0.4em",
            ),

            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Assessment Name",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#475569",
                            flex="2",
                            text_align="left",
                        ),
                        rx.text(
                            "Total Tests",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#475569",
                            flex="1",
                            text_align="center",
                        ),
                        rx.text(
                            "Tests Completed",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#475569",
                            flex="1",
                            text_align="center",
                        ),
                        rx.text(
                            "Tests Not Completed",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#475569",
                            flex="1",
                            text_align="center",
                        ),
                        rx.text(
                            "Action",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#475569",
                            flex="1",
                            text_align="center",
                        ),
                        width="100%",
                        align_items="center",
                        padding="0.8em 1.2em",
                        background="#F8FAFC",
                        border_bottom=f"1px solid {COLORS['line']}",
                        border_radius="10px 10px 0 0",
                    ),

                    rx.cond(
                        CandidateState.dashboard_assessment_summary.length() == 0,
                        rx.box(
                            rx.text(
                                "No assessments assigned to you yet.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                                font_style="italic",
                            ),
                            padding="2em",
                            text_align="center",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.foreach(
                                CandidateState.dashboard_assessment_summary,
                                _summary_table_row,
                            ),
                            spacing="0",
                            width="100%",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                border=f"1px solid {COLORS['line']}",
                border_radius="10px",
                overflow="hidden",
                width="100%",
            ),

            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        background="white",
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.5em",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Recent Activity Section (at the bottom)
# ─────────────────────────────────────────────────────────────────────────────

def _activity_timeline_row(act: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.box(
                width="8px",
                height="8px",
                border_radius="50%",
                background="#7C3AED",
                box_shadow="0 0 0 2px #EDE9FE",
                margin_top="0.35em",
                flex_shrink="0",
            ),
            rx.box(
                width="2px",
                flex="1",
                min_height="24px",
                background="#E2E8F0",
            ),
            align_items="center",
            width="16px",
            height="100%",
            spacing="0",
            flex_shrink="0",
        ),

        rx.hstack(
            rx.text(
                act["name"],
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.cond(
                act["status"] != "",
                rx.match(
                    act["status"],
                    ("Submitted", rx.box(
                        rx.text("Submitted", font_family=FONT_BODY, size="1", weight="medium", color="#027A48"),
                        background="#ECFDF5",
                        border="1px solid #A6F4C5",
                        padding="0.15em 0.65em",
                        border_radius="999px",
                    )),
                    ("Started", rx.box(
                        rx.text("Started", font_family=FONT_BODY, size="1", weight="medium", color="#1D4ED8"),
                        background="#EFF6FF",
                        border="1px solid #BFDBFE",
                        padding="0.15em 0.65em",
                        border_radius="999px",
                    )),
                    rx.box(
                        rx.text(act["status"], font_family=FONT_BODY, size="1", weight="medium", color=COLORS["slate"]),
                        background="#F1F5F9",
                        border=f"1px solid {COLORS['line']}",
                        padding="0.15em 0.65em",
                        border_radius="999px",
                    ),
                ),
                rx.fragment(),
            ),
            spacing="3",
            align_items="center",
        ),

        rx.spacer(),

        rx.text(
            act["timestamp"],
            font_family=FONT_BODY,
            size="2",
            color=COLORS["slate"],
            white_space="nowrap",
        ),

        width="100%",
        align_items="start",
        padding_y="0.35em",
        spacing="3",
    )


def _recent_activity_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("clock", size=18, color="#7C3AED"),
                        background="#F5F3FF",
                        padding="0.55em",
                        border_radius="8px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text(
                        "Recent Activity",
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.link(
                    "View All",
                    href="/candidate/results",
                    color="#7C3AED",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    text_decoration="none",
                    _hover={"text_decoration": "underline", "color": "#6D28D9"},
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.4em",
            ),

            rx.cond(
                CandidateState.dashboard_recent_activities.length() == 0,
                rx.box(
                    rx.text(
                        "No recent activity recorded yet.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                        font_style="italic",
                    ),
                    padding="1.2em 0.4em",
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        CandidateState.dashboard_recent_activities,
                        _activity_timeline_row,
                    ),
                    spacing="0",
                    width="100%",
                    padding_top="0.4em",
                ),
            ),

            spacing="2",
            width="100%",
            align_items="stretch",
        ),
        background="white",
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.5em",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Interactive Popups (Modals)
# ─────────────────────────────────────────────────────────────────────────────

# --- Popup 1: All My Assessments Modal ---
def all_my_assessments_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-text", size=20, color="#7C3AED"),
                            background="#F5F3FF",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.dialog.title(
                                "All My Assessments",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.dialog.description(
                                "List of assessments assigned to you.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_all_assessments_modal,
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Table
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Assessment Name", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="2", text_align="left"),
                            rx.text("Total Tests", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            rx.text("Tests Completed", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            rx.text("Tests Not Completed", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            width="100%",
                            padding="0.75em 1em",
                            background="#F8FAFC",
                            border_bottom=f"1px solid {COLORS['line']}",
                            border_radius="8px 8px 0 0",
                        ),
                        rx.cond(
                            CandidateState.dashboard_assessment_summary.length() == 0,
                            rx.box(
                                rx.text("No assessments assigned to you.", font_family=FONT_BODY, size="2", color=COLORS["slate"], font_style="italic"),
                                padding="2em",
                                text_align="center",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    CandidateState.dashboard_assessment_summary,
                                    lambda item: rx.box(
                                        rx.hstack(
                                            rx.text(item["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], flex="2", text_align="left"),
                                            rx.text(item["total_tests"].to_string(), font_family=FONT_BODY, size="2", color=COLORS["ink"], flex="1", text_align="center"),
                                            rx.text(item["completed_tests"].to_string(), font_family=FONT_BODY, size="2", color=COLORS["ink"], flex="1", text_align="center"),
                                            rx.text(item["not_completed_tests"].to_string(), font_family=FONT_BODY, size="2", color=COLORS["ink"], flex="1", text_align="center"),
                                            width="100%",
                                            align_items="center",
                                            padding="0.75em 1em",
                                        ),
                                        border_bottom=f"1px solid {COLORS['line']}",
                                        width="100%",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                        ),
                        spacing="0",
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                    max_height="320px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_all_assessments_modal,
                            border_radius="8px",
                        ),
                    ),
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="560px",
            background="white",
            border_radius="16px",
            padding="1.6em",
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=CandidateState.show_all_assessments_modal,
        on_open_change=CandidateState.set_show_all_assessments_modal,
    )


# --- Popup 2: Completed Tests Modal ---
def completed_tests_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("circle-check", size=20, color="#7C3AED"),
                            background="#F5F3FF",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.dialog.title(
                                "Completed Tests",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.dialog.description(
                                "Tests you have completed for the selected assessment (" + CandidateState.dashboard_selected_assessment + ").",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_completed_tests_modal,
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Table
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="2", text_align="left"),
                            rx.text("Test Status", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            width="100%",
                            padding="0.75em 1em",
                            background="#F8FAFC",
                            border_bottom=f"1px solid {COLORS['line']}",
                            border_radius="8px 8px 0 0",
                        ),
                        rx.cond(
                            CandidateState.completed_tests_modal_items.length() == 0,
                            rx.box(
                                rx.text("No completed tests found for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], font_style="italic"),
                                padding="2em",
                                text_align="center",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    CandidateState.completed_tests_modal_items,
                                    lambda item: rx.box(
                                        rx.hstack(
                                            rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], flex="2", text_align="left"),
                                            rx.text(item["status"], font_family=FONT_BODY, size="2", color="#475569", flex="1", text_align="center"),
                                            width="100%",
                                            align_items="center",
                                            padding="0.75em 1em",
                                        ),
                                        border_bottom=f"1px solid {COLORS['line']}",
                                        width="100%",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                        ),
                        spacing="0",
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                    max_height="320px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_completed_tests_modal,
                            border_radius="8px",
                        ),
                    ),
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
            background="white",
            border_radius="16px",
            padding="1.6em",
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=CandidateState.show_completed_tests_modal,
        on_open_change=CandidateState.set_show_completed_tests_modal,
    )


# --- Popup 3: Not Completed Tests Modal ---
def not_completed_tests_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("clock", size=20, color="#7C3AED"),
                            background="#F5F3FF",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.dialog.title(
                                "Not Completed Tests",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.dialog.description(
                                "Tests you have not completed for the selected assessment (" + CandidateState.dashboard_selected_assessment + ").",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_not_completed_tests_modal,
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Table
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="2", text_align="left"),
                            rx.text("Test Status", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            width="100%",
                            padding="0.75em 1em",
                            background="#F8FAFC",
                            border_bottom=f"1px solid {COLORS['line']}",
                            border_radius="8px 8px 0 0",
                        ),
                        rx.cond(
                            CandidateState.not_completed_tests_modal_items.length() == 0,
                            rx.box(
                                rx.text("All tests have been completed for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], font_style="italic"),
                                padding="2em",
                                text_align="center",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    CandidateState.not_completed_tests_modal_items,
                                    lambda item: rx.box(
                                        rx.hstack(
                                            rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], flex="2", text_align="left"),
                                            rx.text(item["status"], font_family=FONT_BODY, size="2", color="#475569", flex="1", text_align="center"),
                                            width="100%",
                                            align_items="center",
                                            padding="0.75em 1em",
                                        ),
                                        border_bottom=f"1px solid {COLORS['line']}",
                                        width="100%",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                        ),
                        spacing="0",
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                    max_height="320px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_not_completed_tests_modal,
                            border_radius="8px",
                        ),
                    ),
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
            background="white",
            border_radius="16px",
            padding="1.6em",
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=CandidateState.show_not_completed_tests_modal,
        on_open_change=CandidateState.set_show_not_completed_tests_modal,
    )


# --- Popup 4: Evaluated Tests Modal ---
def evaluated_tests_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("circle-check", size=20, color="#10B981"),
                            background="#ECFDF5",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.dialog.title(
                                "Evaluated Tests",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.dialog.description(
                                "Tests that have been evaluated for the selected assessment (" + CandidateState.dashboard_selected_assessment + ").",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_evaluated_tests_modal,
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Table
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="2", text_align="left"),
                            rx.text("Result", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            width="100%",
                            padding="0.75em 1em",
                            background="#F8FAFC",
                            border_bottom=f"1px solid {COLORS['line']}",
                            border_radius="8px 8px 0 0",
                        ),
                        rx.cond(
                            CandidateState.evaluated_tests_modal_items.length() == 0,
                            rx.box(
                                rx.text("No tests evaluated yet for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], font_style="italic"),
                                padding="2em",
                                text_align="center",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    CandidateState.evaluated_tests_modal_items,
                                    lambda item: rx.box(
                                        rx.hstack(
                                            rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], flex="2", text_align="left"),
                                            rx.box(
                                                rx.cond(
                                                    item["result"] == "Pass",
                                                    rx.box(
                                                        rx.text("Pass", font_family=FONT_BODY, size="1", weight="bold", color="#027A48"),
                                                        background="#ECFDF5",
                                                        border="1px solid #A6F4C5",
                                                        padding="0.2em 0.8em",
                                                        border_radius="999px",
                                                    ),
                                                    rx.box(
                                                        rx.text("Fail", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626"),
                                                        background="#FEF2F2",
                                                        border="1px solid #FECACA",
                                                        padding="0.2em 0.8em",
                                                        border_radius="999px",
                                                    ),
                                                ),
                                                flex="1",
                                                display="flex",
                                                justify_content="center",
                                            ),
                                            width="100%",
                                            align_items="center",
                                            padding="0.75em 1em",
                                        ),
                                        border_bottom=f"1px solid {COLORS['line']}",
                                        width="100%",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                        ),
                        spacing="0",
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                    max_height="320px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_evaluated_tests_modal,
                            border_radius="8px",
                        ),
                    ),
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
            background="white",
            border_radius="16px",
            padding="1.6em",
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=CandidateState.show_evaluated_tests_modal,
        on_open_change=CandidateState.set_show_evaluated_tests_modal,
    )


# --- Popup 5: Pending Evaluation Modal ---
def pending_evaluation_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("clock", size=20, color="#EF4444"),
                            background="#FEF2F2",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.dialog.title(
                                "Pending Evaluation",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.dialog.description(
                                "Submitted tests pending evaluation for the selected assessment (" + CandidateState.dashboard_selected_assessment + ").",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_pending_evaluation_modal,
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Table
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="2", text_align="left"),
                            rx.text("Result", font_family=FONT_BODY, size="2", weight="bold", color="#475569", flex="1", text_align="center"),
                            width="100%",
                            padding="0.75em 1em",
                            background="#F8FAFC",
                            border_bottom=f"1px solid {COLORS['line']}",
                            border_radius="8px 8px 0 0",
                        ),
                        rx.cond(
                            CandidateState.pending_evaluation_modal_items.length() == 0,
                            rx.box(
                                rx.text("No tests currently pending evaluation for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], font_style="italic"),
                                padding="2em",
                                text_align="center",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    CandidateState.pending_evaluation_modal_items,
                                    lambda item: rx.box(
                                        rx.hstack(
                                            rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], flex="2", text_align="left"),
                                            rx.box(
                                                rx.box(
                                                    rx.text("Pending Evaluation", font_family=FONT_BODY, size="1", weight="medium", color="#B45309"),
                                                    background="#FEF3C7",
                                                    border="1px solid #FDE68A",
                                                    padding="0.2em 0.8em",
                                                    border_radius="999px",
                                                ),
                                                flex="1",
                                                display="flex",
                                                justify_content="center",
                                            ),
                                            width="100%",
                                            align_items="center",
                                            padding="0.75em 1em",
                                        ),
                                        border_bottom=f"1px solid {COLORS['line']}",
                                        width="100%",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                        ),
                        spacing="0",
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                    max_height="320px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=CandidateState.close_pending_evaluation_modal,
                            border_radius="8px",
                        ),
                    ),
                    width="100%",
                    padding_top="0.6em",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
            background="white",
            border_radius="16px",
            padding="1.6em",
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=CandidateState.show_pending_evaluation_modal,
        on_open_change=CandidateState.set_show_pending_evaluation_modal,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Candidate Dashboard Page Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def candidate_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # 1. Welcome Banner
        _welcome_banner(),

        # 2. Three Statistics & Donut Cards in one row
        _statistics_row(),

        # 3. Assessment Summary Full-width Card
        _assessment_summary_card(),

        # 4. Recent Activity Vertical Timeline at Bottom
        _recent_activity_card(),

        # 5. Interactive Popups (Modals)
        all_my_assessments_modal(),
        completed_tests_modal(),
        not_completed_tests_modal(),
        evaluated_tests_modal(),
        pending_evaluation_modal(),

        spacing="5",
        width="100%",
        align_items="stretch",
    )

    return candidate_shell(
        "dashboard",
        "Dashboard",
        "Track your assessments and progress.",
        content,
    )
