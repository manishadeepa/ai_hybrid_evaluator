"""
Candidate Dashboard — My Assessments
Shows assessments assigned to the logged-in candidate.
Availability per test is determined by whether the facilitator has uploaded a question paper.
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.candidate_shell import candidate_shell
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.state.candidate_state import CandidateState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────────────────────
# Status Badge — matches the style used in facilitator dashboard
# ─────────────────────────────────────────────────────────────────────────────

def _status_badge(status: str) -> rx.Component:
    return rx.match(
        status,
        ("Draft", rx.box(
            rx.text("Draft", font_family=FONT_BODY, size="1", weight="medium", color="#667085"),
            background="#F2F4F7", padding="0.3em 0.8em", border_radius="999px",
        )),
        ("Scheduled", rx.box(
            rx.text("Scheduled", font_family=FONT_BODY, size="1", weight="medium", color="#B54708"),
            background="#FFFAEB", padding="0.3em 0.8em", border_radius="999px",
        )),
        ("Active", rx.box(
            rx.text("Active", font_family=FONT_BODY, size="1", weight="medium", color=COLORS["primary"]),
            background=COLORS["primary_soft"], padding="0.3em 0.8em", border_radius="999px",
        )),
        rx.box(
            rx.text(status, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["success"]),
            background=COLORS["success_soft"], padding="0.3em 0.8em", border_radius="999px",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test Row — one row per test inside an assessment card
# ─────────────────────────────────────────────────────────────────────────────

def _test_row(assessment_name: str, test_name: str, is_final: bool) -> rx.Component:
    """A single test row showing availability and Start Test / Locked button."""
    has_qp = FacilitatorState.question_papers.get(assessment_name, {}).contains(test_name)

    return rx.box(
        rx.hstack(
            # Left: icon + test name
            rx.hstack(
                rx.cond(
                    is_final,
                    rx.box(
                        rx.icon("award", size=15, color="#B45309"),
                        background="#FEF3C7",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.box(
                        rx.icon("file-text", size=15, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.4em",
                        border_radius="6px",
                    ),
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text(test_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        rx.cond(
                            is_final,
                            rx.badge("Final Evaluation", color_scheme="amber", variant="soft", size="1"),
                            rx.badge("Regular Test", color_scheme="indigo", variant="soft", size="1"),
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    # Availability status text
                    rx.cond(
                        has_qp,
                        rx.hstack(
                            rx.icon("circle-check", size=12, color="#027A48"),
                            rx.text("Available", font_family=FONT_BODY, size="1", color="#027A48", weight="medium"),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.icon("lock", size=12, color="#D97706"),
                            rx.text("Locked — question paper not yet uploaded", font_family=FONT_BODY, size="1", color="#D97706"),
                            spacing="1",
                            align_items="center",
                        ),
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="2",
                align_items="center",
            ),
            rx.spacer(),
            # Right: Start Test / Locked button
            rx.cond(
                has_qp,
                rx.button(
                    rx.icon("play", size=13),
                    "Start Test",
                    on_click=[
                        rx.call_script("if (!document.fullscreenElement) { (document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen || function(){}).call(document.documentElement).catch(function(e){console.warn(e);}); }"),
                        CandidateState.start_test(assessment_name, test_name),
                    ],
                    size="1",
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    _hover={"background": COLORS["primary_hover"]},
                ),
                rx.button(
                    rx.icon("lock", size=13),
                    "Locked",
                    size="1",
                    disabled=True,
                    variant="outline",
                    color_scheme="gray",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    cursor="not-allowed",
                    opacity="0.5",
                ),
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.65em 0.8em",
        border=f"1px solid {COLORS['line']}",
        border_radius="8px",
        background=COLORS["canvas"],
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Assessment Card — shows one assessment with its test list
# The assessment dict from AdminState has:
#   name, assessment_date, facilitator_name, status, tests (list), final_test
# ─────────────────────────────────────────────────────────────────────────────

def candidate_assessment_card(a: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header row
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("clipboard-list", size=18, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.5em",
                        border_radius="8px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.text(a["name"], font_family=FONT_DISPLAY, size="4", weight="bold", color=COLORS["ink"]),
                        rx.hstack(
                            rx.icon("user-check", size=12, color=COLORS["slate"]),
                            rx.text(
                                "Facilitator: ", a["facilitator_name"],
                                font_family=FONT_BODY, size="1", color=COLORS["slate"],
                            ),
                            rx.text("•", color=COLORS["placeholder"], size="1"),
                            rx.icon("calendar", size=12, color=COLORS["slate"]),
                            rx.text(
                                a["assessment_date"],
                                font_family=FONT_BODY, size="1", color=COLORS["slate"],
                            ),
                            spacing="1",
                            align_items="center",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                _status_badge(a["status"]),
                width="100%",
                align_items="start",
            ),

            # Divider
            rx.divider(color_scheme="gray", size="4", margin_y="0.8em"),

            # Tests section header
            rx.hstack(
                rx.icon("list-checks", size=13, color=COLORS["slate"]),
                rx.text(
                    "Tests",
                    font_family=FONT_BODY,
                    size="1",
                    weight="bold",
                    color=COLORS["slate"],
                    letter_spacing="0.05em",
                    text_transform="uppercase",
                ),
                spacing="1",
                align_items="center",
                padding_bottom="0.4em",
            ),

            # Test rows — one static row per test (Reflex can't foreach over runtime list items
            # nested inside a foreach render fn without typed vars, so we render the known
            # "Test 1" + "Final Test" pattern from the mock data)
            _test_row(a["name"], "Test 1", False),
            _test_row(a["name"], a["final_test"], True),

            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.5em",
        width="100%",
        box_shadow="0 1px 4px rgba(0,0,0,0.04)",
        _hover={"box_shadow": "0 4px 12px rgba(0,0,0,0.07)"},
        transition="box-shadow 0.15s ease",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Candidate Dashboard filtered view
# We show all assessments from AdminState where the candidate's emp_id appears
# in the assessment's assigned_candidates list.
# ─────────────────────────────────────────────────────────────────────────────

def _my_assessments_content() -> rx.Component:
    """
    Filters AdminState.assessments where AuthState.candidate_emp_id is in
    the assignment list, then renders cards.
    Uses rx.foreach so the list is reactive to admin changes.
    """
    # We pass ALL assessments through foreach and rely on per-card visibility.
    # The filter is done with rx.cond inside the render fn.
    return rx.foreach(
        AdminState.assessments,
        _maybe_render_assessment_card,
    )


def _maybe_render_assessment_card(a: dict) -> rx.Component:
    """
    Renders a card only if the candidate's ID is in the assessment's
    assigned_candidates list. Otherwise renders an empty fragment.
    """
    is_assigned = a["assigned_candidates"].contains(AuthState.candidate_emp_id)
    return rx.cond(
        is_assigned,
        candidate_assessment_card(a),
        rx.fragment(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────

def candidate_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # ── My Assessments List ──────────────────────────────────────────
        rx.vstack(
            _my_assessments_content(),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )

    return candidate_shell(
        "assessments",
        "My Assessments",
        "Your assigned assessments and test stages are listed below.",
        content,
    )
