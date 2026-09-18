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
    """A single test row showing availability, submission status, Start Test / Submitted / Locked button,
    and — once evaluated — the candidate's normalized score."""
    has_qp = FacilitatorState.question_papers.get(assessment_name, {}).contains(test_name)
    is_submitted = CandidateState.submitted_tests.get(assessment_name, {}).contains(test_name)
    is_disqualified = CandidateState.disqualified_tests.get(assessment_name, {}).contains(test_name)

    # Score data from the pre-computed flat dicts (composite key: "asmn::test_name")
    _score_key = assessment_name + "::" + test_name
    score_str = CandidateState.candidate_test_scores.get(_score_key, "-")
    is_evaluated = CandidateState.candidate_test_evaluated.get(_score_key, False)

    return rx.box(
        rx.hstack(
            # Left: icon + test name + availability status
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
                    rx.text(test_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    # Availability status text
                    rx.cond(
                        is_submitted,
                        rx.hstack(
                            rx.icon("circle-check", size=12, color="#027A48"),
                            rx.text("Submitted", font_family=FONT_BODY, size="1", color="#027A48", weight="medium"),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.cond(
                            is_disqualified,
                            rx.hstack(
                                rx.icon("shield-alert", size=12, color="#DC2626"),
                                rx.text("Disqualified — Proctoring Policy Violation", font_family=FONT_BODY, size="1", color="#DC2626", weight="medium"),
                                spacing="1",
                                align_items="center",
                            ),
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
                        ),
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="2",
                align_items="center",
                flex="1",
            ),
            rx.spacer(),
            # Centre: Score + Evaluation status (shown once submitted)
            rx.cond(
                is_submitted | is_disqualified,
                rx.cond(
                    is_evaluated,
                    # Evaluated: show score + green badge
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                score_str,
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["primary"],
                            ),
                            rx.text(
                                "Score",
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            align_items="center",
                            spacing="0",
                        ),
                        rx.box(
                            rx.text(
                                "Evaluated",
                                font_family=FONT_BODY,
                                size="1",
                                weight="medium",
                                color="#027A48",
                            ),
                            background="#ECFDF5",
                            border="1px solid #A7F3D0",
                            padding="0.3em 0.75em",
                            border_radius="999px",
                        ),
                        spacing="3",
                        align_items="center",
                        margin_right="0.5em",
                    ),
                    # Submitted but not yet evaluated: show dash + Pending badge
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "-",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["slate"],
                            ),
                            rx.text(
                                "Not Evaluated",
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            align_items="center",
                            spacing="0",
                        ),
                        rx.box(
                            rx.text(
                                "Pending",
                                font_family=FONT_BODY,
                                size="1",
                                weight="medium",
                                color="#B45309",
                            ),
                            background="#FFFBEB",
                            border="1px solid #FDE68A",
                            padding="0.3em 0.75em",
                            border_radius="999px",
                        ),
                        spacing="3",
                        align_items="center",
                        margin_right="0.5em",
                    ),
                ),
                rx.fragment(),  # Not submitted yet — no score column
            ),
            # Right: Action button
            rx.cond(
                is_submitted,
                rx.button(
                    rx.icon("check", size=13),
                    "Submitted",
                    size="1",
                    disabled=True,
                    variant="soft",
                    color_scheme="green",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    cursor="default",
                ),
                rx.cond(
                    is_disqualified,
                    rx.button(
                        rx.icon("shield-alert", size=13),
                        "Disqualified",
                        size="1",
                        disabled=True,
                        variant="soft",
                        color_scheme="red",
                        font_family=FONT_BODY,
                        border_radius="6px",
                        cursor="default",
                    ),
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
#   name, assessment_date, status, tests (list), final_test
# Facilitator details are intentionally hidden from the Candidate view.
# ─────────────────────────────────────────────────────────────────────────────

def candidate_assessment_card(a: dict) -> rx.Component:
    asmn = a["name"]
    overall_score = CandidateState.candidate_overall_scores.get(asmn, "-")
    overall_available = CandidateState.candidate_overall_available.get(asmn, False)

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
                        rx.text(
                            "This assessment consists of multiple tests. You can take the tests as per the schedule. "
                            "Your scores will be visible here once the evaluation is completed.",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="2",
                    align_items="start",
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

            # When no tests configured yet
            rx.cond(
                (a["tests"].length() == 0) & (a["final_test"] == ""),
                rx.box(
                    rx.text(
                        "No tests scheduled yet for this assessment.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                        font_style="italic",
                    ),
                    padding="0.8em 0.2em",
                ),
            ),

            # Test rows — formative tests
            rx.foreach(
                a["tests"],
                lambda t: _test_row(a["name"], t, False),
            ),
            # Summative test row (only when configured)
            rx.cond(
                a["final_test"] != "",
                _test_row(a["name"], a["final_test"], True),
            ),

            # ─── Overall Assessment Score section ────────────────────────────────
            rx.divider(color_scheme="gray", size="4", margin_y="0.6em"),
            rx.hstack(
                # Left: icon + label + description
                rx.hstack(
                    rx.box(
                        rx.icon("trophy", size=18, color="#7C3AED"),
                        background="#F5F3FF",
                        padding="0.5em",
                        border_radius="8px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.text(
                            "Overall Assessment Score",
                            font_family=FONT_DISPLAY,
                            size="3",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "The overall assessment score will be available once all tests are evaluated and the assessment is completed.",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="2",
                    align_items="center",
                    flex="1",
                ),
                rx.spacer(),
                # Right: score box
                rx.cond(
                    overall_available,
                    # Show actual score
                    rx.box(
                        rx.vstack(
                            rx.text(
                                overall_score,
                                font_family=FONT_DISPLAY,
                                size="5",
                                weight="bold",
                                color="#7C3AED",
                            ),
                            rx.text(
                                "Overall Score",
                                font_family=FONT_BODY,
                                size="1",
                                color="#7C3AED",
                            ),
                            spacing="0",
                            align_items="center",
                        ),
                        background="#F5F3FF",
                        border="1px solid #DDD6FE",
                        border_radius="10px",
                        padding="0.8em 1.4em",
                    ),
                    # Not yet available
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "-",
                                font_family=FONT_DISPLAY,
                                size="5",
                                weight="bold",
                                color=COLORS["slate"],
                            ),
                            rx.text(
                                "Not Available Yet",
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="center",
                        ),
                        background="#F9FAFB",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="10px",
                        padding="0.8em 1.4em",
                    ),
                ),
                width="100%",
                align_items="center",
            ),

            # Info note
            rx.hstack(
                rx.icon("info", size=13, color=COLORS["primary"]),
                rx.text(
                    "Your overall score will be calculated based on the finalized weightage for each test as defined by your facilitator.",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="2",
                align_items="start",
                background=COLORS["primary_soft"],
                border=f"1px solid #DDD6FE",
                border_radius="8px",
                padding="0.6em 0.9em",
                width="100%",
            ),

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
