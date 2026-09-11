"""
My Assessments — the Facilitator's landing page.
Shows only the assessments Admin has assigned to the currently signed-in
facilitator. Test information is NOT shown here — tests are managed inside
the Assessment Workspace.
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import qp_preview_dialog
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


# ─────────────────────────────────────────────────────────────────────
# Status badge
# ─────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────
# Approval action row (pending / declined banners)
# ─────────────────────────────────────────────────────────────────────
def approval_action_row(a: dict, idx: int) -> rx.Component:
    return rx.cond(
        a["approval_status"] == "pending",
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.icon("bell", size=13, color="#B45309"),
                    rx.text(
                        "This assessment was created/updated by admin. Please review and respond.",
                        font_family=FONT_BODY, size="1", color="#92400E", weight="medium",
                    ),
                    spacing="1", align_items="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("check", size=13), "Approve",
                    on_click=FacilitatorState.approve_assessment(a["name"]),
                    size="1", background="#027A48", color="white",
                    font_family=FONT_BODY, border_radius="6px",
                    _hover={"background": "#065F46"},
                ),
                rx.button(
                    rx.icon("x", size=13), "Decline",
                    on_click=FacilitatorState.decline_assessment(a["name"]),
                    size="1", background="#FEF2F2", color="#991B1B",
                    border="1px solid #FECACA",
                    font_family=FONT_BODY, border_radius="6px",
                    _hover={"background": "#FEE2E2"},
                ),
                spacing="2", align_items="center", width="100%",
            ),
            background="#FFFBEB", border="1px solid #FDE68A",
            border_radius="8px", padding="0.65em 1em",
            width="100%", margin_top="0.8em",
        ),
        rx.cond(
            a["approval_status"] == "declined",
            rx.box(
                rx.hstack(
                    rx.icon("circle-x", size=13, color="#991B1B"),
                    rx.text(
                        "You have declined this assessment.",
                        font_family=FONT_BODY, size="1", color="#991B1B", weight="medium",
                    ),
                    spacing="1", align_items="center",
                ),
                background="#FEF2F2", border="1px solid #FECACA",
                border_radius="8px", padding="0.55em 1em",
                width="100%", margin_top="0.8em",
            ),
            rx.fragment(),
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# Assessment card — clean design, NO test info
# ─────────────────────────────────────────────────────────────────────
def assessment_card(a: dict, idx: int) -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: colored icon square
            rx.box(
                rx.icon("clipboard-check", size=22, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="0.7em",
                border_radius="10px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Centre: name + meta
            rx.vstack(
                rx.text(
                    a["name"],
                    font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"],
                ),
                rx.hstack(
                    rx.icon("users", size=12, color=COLORS["slate"]),
                    rx.text(
                        a["candidate_details"].length().to_string() + " candidates",
                        font_family=FONT_BODY, size="2", color=COLORS["slate"],
                    ),
                    rx.text("·", font_family=FONT_BODY, size="2", color=COLORS["placeholder"]),
                    rx.icon("user", size=12, color=COLORS["slate"]),
                    rx.text(
                        rx.cond(
                            AuthState.facilitator_name != "",
                            AuthState.facilitator_name + " (Facilitator)",
                            a["facilitator_name"] + " (Facilitator)",
                        ),
                        font_family=FONT_BODY, size="2", color=COLORS["slate"],
                    ),
                    spacing="1", align_items="center", flex_wrap="wrap",
                ),
                # Date row
                rx.hstack(
                    rx.icon("calendar", size=12, color=COLORS["slate"]),
                    rx.cond(
                        a["assessment_date"] != "",
                        rx.text(
                            a["assessment_date"],
                            font_family=FONT_BODY, size="1", color=COLORS["placeholder"],
                        ),
                        rx.text(
                            "Date not set",
                            font_family=FONT_BODY, size="1", color=COLORS["placeholder"],
                        ),
                    ),
                    spacing="1", align_items="center",
                ),
                spacing="1", align_items="start", flex="1",
            ),
            rx.spacer(),
            # Right: status badge + Open button (hidden when declined)
            rx.vstack(
                status_badge(a["status"]),
                rx.cond(
                    a["approval_status"] != "declined",
                    rx.button(
                        "Open Assessment",
                        rx.icon("arrow-right", size=14),
                        on_click=FacilitatorState.open_assessment(idx),
                        size="2",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        _hover={"background": COLORS["primary_hover"]},
                        cursor="pointer",
                        margin_top="0.5em",
                    ),
                ),
                align_items="end",
                spacing="1",
            ),
            align_items="start",
            width="100%",
            spacing="4",
        ),
        # Approval/declined banners
        approval_action_row(a, idx),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.3em 1.5em",
        width="100%",
        transition="box-shadow 0.15s ease",
        _hover={"box_shadow": "0 2px 12px 0 rgba(109,40,217,0.07)"},
    )


# ─────────────────────────────────────────────────────────────────────
# Empty state
# ─────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────
# Info box (bottom of page)
# ─────────────────────────────────────────────────────────────────────
def info_box() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("info", size=18, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="0.5em",
                border_radius="8px",
                display="flex", align_items="center", justify_content="center",
            ),
            rx.text(
                "Only assigned assessments are shown here. Tests can be created and managed after opening an assessment.",
                font_family=FONT_BODY, size="2", color=COLORS["primary"], weight="medium",
                line_height="1.5",
            ),
            spacing="3", align_items="center", width="100%",
        ),
        background="#F5F3FF",
        border="1px solid #DDD6FE",
        border_radius="12px",
        padding="0.9em 1.2em",
        width="100%",
        margin_top="1em",
    )


# ─────────────────────────────────────────────────────────────────────
# Search bar var — stored on FacilitatorState
# ─────────────────────────────────────────────────────────────────────
def search_bar() -> rx.Component:
    return rx.box(
        rx.input(
            rx.input.slot(rx.icon("search", size=15, color=COLORS["slate"])),
            placeholder="Search assessments...",
            value=FacilitatorState.assessment_search_query,
            on_change=FacilitatorState.set_assessment_search_query,
            size="2",
            width="100%",
            font_family=FONT_BODY,
            border_radius="8px",
        ),
        width="100%",
        max_width="400px",
    )


# ─────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────
def facilitator_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # Search row
        rx.hstack(
            search_bar(),
            rx.spacer(),
            spacing="0",
            width="100%",
            padding_bottom="1em",
        ),
        # Assessment list (filtered)
        rx.cond(
            FacilitatorState.filtered_my_assessments.length() == 0,
            rx.cond(
                FacilitatorState.my_assessments.length() == 0,
                empty_state(),
                # Has assessments but search yielded nothing
                rx.box(
                    rx.vstack(
                        rx.icon("search-x", size=24, color=COLORS["slate"]),
                        rx.text("No assessments match your search.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                        align_items="center",
                    ),
                    background=COLORS["surface"],
                    border=f"1px dashed {COLORS['line']}",
                    border_radius="12px",
                    padding="3em",
                    width="100%",
                ),
            ),
            rx.vstack(
                rx.foreach(FacilitatorState.filtered_my_assessments, assessment_card),
                spacing="3",
                width="100%",
            ),
        ),
        qp_preview_dialog(),
        info_box(),
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