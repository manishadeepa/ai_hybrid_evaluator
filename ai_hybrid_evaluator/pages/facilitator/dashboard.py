"""
My Assessments — the Facilitator's landing page.
Shows only the assessments Admin has assigned to the currently signed-in
facilitator, each expanded with the list of assigned candidates.
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import qp_preview_dialog
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def status_badge(status: str) -> rx.Component:
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


def candidate_row(c: dict) -> rx.Component:
    """A single candidate row shown inside the expanded assessment card."""
    return rx.hstack(
        rx.box(
            rx.icon("user", size=13, color=COLORS["primary"]),
            background=COLORS["primary_soft"],
            padding="0.3em",
            border_radius="6px",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.text(
            c["name"],
            font_family=FONT_BODY,
            size="2",
            weight="medium",
            color=COLORS["ink"],
            min_width="140px",
        ),
        rx.text(
            c["emp_id"],
            font_family=FONT_BODY,
            size="1",
            color=COLORS["slate"],
            background=COLORS["canvas"],
            padding="0.15em 0.5em",
            border_radius="4px",
            border=f"1px solid {COLORS['line']}",
        ),
        rx.text(
            c["email"],
            font_family=FONT_BODY,
            size="1",
            color=COLORS["slate"],
        ),
        spacing="2",
        align_items="center",
        width="100%",
        padding="0.4em 0",
    )


def candidate_list_section(candidates: list) -> rx.Component:
    """Expandable section showing all candidates for an assessment."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("users", size=13, color=COLORS["slate"]),
                rx.text(
                    "Assigned Candidates",
                    font_family=FONT_BODY,
                    size="1",
                    weight="bold",
                    color=COLORS["slate"],
                    letter_spacing="0.05em",
                    text_transform="uppercase",
                ),
                spacing="1",
                align_items="center",
                padding_bottom="0.5em",
            ),
            rx.foreach(candidates, candidate_row),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        padding_top="1em",
        margin_top="1em",
        border_top=f"1px solid {COLORS['line']}",
        width="100%",
    )

def approval_action_row(a: dict, idx: int) -> rx.Component:
    """Banner shown when approval_status == 'pending' (admin just created/updated the assessment)."""
    return rx.cond(
        a["approval_status"] == "pending",
        # ── Pending: show Approve / Decline buttons ──
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.icon("bell", size=13, color="#B45309"),
                    rx.text(
                        "This assessment was created/updated by admin. Please review and respond.",
                        font_family=FONT_BODY,
                        size="1",
                        color="#92400E",
                        weight="medium",
                    ),
                    spacing="1",
                    align_items="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("check", size=13),
                    "Approve",
                    on_click=FacilitatorState.approve_assessment(a["name"]),
                    size="1",
                    background="#027A48",
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    _hover={"background": "#065F46"},
                ),
                rx.button(
                    rx.icon("x", size=13),
                    "Decline",
                    on_click=FacilitatorState.decline_assessment(a["name"]),
                    size="1",
                    background="#FEF2F2",
                    color="#991B1B",
                    border=f"1px solid #FECACA",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    _hover={"background": "#FEE2E2"},
                ),
                spacing="2",
                align_items="center",
                width="100%",
            ),
            background="#FFFBEB",
            border=f"1px solid #FDE68A",
            border_radius="8px",
            padding="0.65em 1em",
            width="100%",
            margin_top="0.8em",
        ),
        rx.cond(
            a["approval_status"] == "declined",
            # ── Declined: show a muted notice ──
            rx.box(
                rx.hstack(
                    rx.icon("circle-x", size=13, color="#991B1B"),
                    rx.text(
                        "You have declined this assessment.",
                        font_family=FONT_BODY,
                        size="1",
                        color="#991B1B",
                        weight="medium",
                    ),
                    spacing="1",
                    align_items="center",
                ),
                background="#FEF2F2",
                border="1px solid #FECACA",
                border_radius="8px",
                padding="0.55em 1em",
                width="100%",
                margin_top="0.8em",
            ),
            # ── Approved: render nothing extra ──
            rx.fragment(),
        ),
    )



def dashboard_test_item(assessment_name: str, test_name: str, is_final: bool) -> rx.Component:
    """Row for an individual test showing test-wise question paper status."""
    has_qp = FacilitatorState.question_papers.get(assessment_name, {}).contains(test_name)
    fname = FacilitatorState.question_papers.get(assessment_name, {}).get(test_name, "")
    return rx.box(
        rx.hstack(
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
                    rx.cond(
                        has_qp,
                        rx.hstack(
                            rx.icon("circle-check", size=12, color="#027A48"),
                            rx.text("QP: " + fname, font_family=FONT_BODY, size="1", color="#027A48", weight="medium"),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.icon("clock", size=12, color="#D97706"),
                            rx.text("Question Paper Pending", font_family=FONT_BODY, size="1", color="#D97706"),
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
            rx.hstack(
                rx.cond(
                    has_qp,
                    rx.button(
                        rx.icon("eye", size=12),
                        "View",
                        on_click=FacilitatorState.open_qp_preview(test_name, assessment_name),
                        size="1",
                        variant="soft",
                        color_scheme="indigo",
                        font_family=FONT_BODY,
                    ),
                ),
                rx.button(
                    rx.cond(has_qp, "Manage QP", "Upload QP"),
                    rx.icon("arrow-up-right", size=13),
                    on_click=FacilitatorState.open_assessment_test(assessment_name, test_name),
                    size="1",
                    variant=rx.cond(has_qp, "outline", "solid"),
                    color_scheme=rx.cond(has_qp, "gray", "indigo"),
                    font_family=FONT_BODY,
                ),
                spacing="2",
                align_items="center",
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.6em 0.8em",
        border=f"1px solid {COLORS['line']}",
        border_radius="8px",
        background=COLORS["canvas"],
        width="100%",
    )


def test_wise_section(a: dict) -> rx.Component:
    """Expandable section showing test-wise question papers and stages."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("layers", size=13, color=COLORS["slate"]),
                rx.text(
                    "Test-Wise Question Papers",
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
            rx.vstack(
                rx.foreach(
                    a["tests"],
                    lambda t: dashboard_test_item(a["name"], t, False),
                ),
                dashboard_test_item(a["name"], a["final_test"], True),
                spacing="2",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        padding_top="1em",
        margin_top="1em",
        border_top=f"1px solid {COLORS['line']}",
        width="100%",
    )


def assessment_card(a: dict, idx: int) -> rx.Component:
    return rx.box(
        rx.vstack(
            # ── Header row ──────────────────────────────────────────────
            rx.hstack(
                rx.vstack(
                    rx.text(
                        a["name"],
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.icon("calendar", size=13, color=COLORS["slate"]),
                        rx.text(
                            a["assessment_date"],
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.icon("users", size=13, color=COLORS["slate"], margin_left="0.8em"),
                        rx.text(
                            a["candidate_details"].length().to_string() + " candidates",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        spacing="1",
                        align_items="center",
                        padding_top="0.3em",
                    ),
                    rx.hstack(
                        rx.foreach(
                            a["tests"],
                            lambda t: rx.badge(
                                rx.icon("file-text", size=11),
                                t,
                                color_scheme="indigo",
                                variant="soft",
                                size="1",
                                font_family=FONT_BODY,
                            ),
                        ),
                        rx.badge(
                            rx.icon("award", size=11),
                            a["final_test"],
                            color_scheme="amber",
                            variant="soft",
                            size="1",
                            font_family=FONT_BODY,
                        ),
                        spacing="1",
                        align_items="center",
                        padding_top="0.3em",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                status_badge(a["status"]),
                # Open button — hidden when assessment is declined
                rx.cond(
                    a["approval_status"] != "declined",
                    rx.button(
                        "Open",
                        rx.icon("arrow-right", size=14),
                        on_click=FacilitatorState.open_assessment(idx),
                        size="2",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        margin_left="1.2em",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                ),
                align_items="center",
                width="100%",
            ),
            # ── Approve / Decline banner (or Declined notice) ────────────
            approval_action_row(a, idx),
            # ── Test-wise Question Papers (shown for approved assessments) ──
            rx.cond(
                a["approval_status"] == "approved",
                test_wise_section(a),
            ),
            # ── Candidate list (always visible) ─────────────────────────
            rx.cond(
                a["candidate_details"].length() > 0,
                candidate_list_section(a["candidate_details"]),
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.3em 1.5em",
        width="100%",
    )


def empty_state() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("clipboard-list", size=28, color=COLORS["slate"]),
            rx.text(
                "No assessments assigned yet.",
                font_family=FONT_BODY, size="2", color=COLORS["slate"], padding_top="0.6em",
            ),
            align_items="center",
        ),
        background=COLORS["surface"],
        border=f"1px dashed {COLORS['line']}",
        border_radius="12px",
        padding="3em",
        width="100%",
    )


def facilitator_dashboard_page() -> rx.Component:
    content = rx.vstack(
        rx.cond(
            FacilitatorState.my_assessments.length() == 0,
            empty_state(),
            rx.vstack(
                rx.foreach(FacilitatorState.my_assessments, assessment_card),
                spacing="3",
                width="100%",
            ),
        ),
        qp_preview_dialog(),
        spacing="0",
        width="100%",
        align_items="stretch",
    )
    return facilitator_shell(
        active="assessments",
        title="My Assessments",
        subtitle=f"{FacilitatorState.my_total_candidates} candidates assigned to you across all assessments.",
        content=content,
    )