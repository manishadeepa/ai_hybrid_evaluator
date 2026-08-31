"""Admin Reports page — assessment-level breakdown using live AdminState data."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


# ─────────────────────────────────────────────────────────────
# Summary stat card
# ─────────────────────────────────────────────────────────────

def report_stat_card(
    label: str,
    value: rx.Var,
    icon: str,
    icon_color: str,
    icon_bg: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=20, color=icon_color),
                background=icon_bg,
                padding="0.75em",
                border_radius="10px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(label, font_family=FONT_BODY, size="1",
                        color=COLORS["slate"], weight="medium"),
                rx.text(value, font_family=FONT_BODY, size="5",
                        weight="bold", color=COLORS["ink"]),
                spacing="0",
                align_items="start",
            ),
            spacing="3",
            align_items="center",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em 1.5em",
        flex="1",
    )


# ─────────────────────────────────────────────────────────────
# Approval status badge
# ─────────────────────────────────────────────────────────────

def approval_badge(status: str) -> rx.Component:
    return rx.match(
        status,
        ("approved", rx.hstack(
            rx.icon("circle-check", size=13, color="#027A48"),
            rx.text("Approved", font_family=FONT_BODY, size="1",
                    weight="medium", color="#027A48"),
            spacing="1", align_items="center",
            background="#ECFDF3", border="1px solid #A6F4C5",
            padding="0.25em 0.7em", border_radius="999px",
        )),
        ("declined", rx.hstack(
            rx.icon("circle-x", size=13, color="#991B1B"),
            rx.text("Declined", font_family=FONT_BODY, size="1",
                    weight="medium", color="#991B1B"),
            spacing="1", align_items="center",
            background="#FEF2F2", border="1px solid #FECACA",
            padding="0.25em 0.7em", border_radius="999px",
        )),
        rx.hstack(
            rx.icon("clock", size=13, color="#B45309"),
            rx.text("Awaiting", font_family=FONT_BODY, size="1",
                    weight="medium", color="#B45309"),
            spacing="1", align_items="center",
            background="#FFFBEB", border="1px solid #FDE68A",
            padding="0.25em 0.7em", border_radius="999px",
        ),
    )


def assessment_status_badge(status: str) -> rx.Component:
    return rx.match(
        status,
        ("Scheduled", rx.badge("Scheduled", color_scheme="orange",
                               variant="soft", size="1", font_family=FONT_BODY)),
        ("Active", rx.badge("Active", color_scheme="indigo",
                            variant="soft", size="1", font_family=FONT_BODY)),
        ("Completed", rx.badge("Completed", color_scheme="green",
                               variant="soft", size="1", font_family=FONT_BODY)),
        rx.badge("Draft", color_scheme="gray",
                 variant="soft", size="1", font_family=FONT_BODY),
    )


# ─────────────────────────────────────────────────────────────
# Assessment report row
# ─────────────────────────────────────────────────────────────

def report_row(a: dict) -> rx.Component:
    return rx.table.row(
        # Assessment name
        rx.table.cell(
            rx.text(a["name"], font_family=FONT_BODY, size="2",
                    weight="bold", color=COLORS["ink"]),
        ),
        # Date
        rx.table.cell(
            rx.text(a["assessment_date"], font_family=FONT_BODY,
                    size="2", color=COLORS["slate"]),
        ),
        # Facilitator
        rx.table.cell(
            rx.text(a["facilitator_name"], font_family=FONT_BODY,
                    size="2", color=COLORS["slate"]),
        ),
        # Candidates
        rx.table.cell(
            rx.text(
                a["assigned_candidates"].length().to_string() + " candidates",
                font_family=FONT_BODY, size="2", color=COLORS["slate"],
            ),
        ),
        # Tests count
        rx.table.cell(
            rx.text(
                a["tests"].length().to_string() + " + Final",
                font_family=FONT_BODY, size="2", color=COLORS["slate"],
            ),
        ),
        # Assessment status
        rx.table.cell(assessment_status_badge(a["status"])),
        # Facilitator response
        rx.table.cell(approval_badge(a.get("approval_status", "pending"))),
    )


# ─────────────────────────────────────────────────────────────
# Reports page
# ─────────────────────────────────────────────────────────────

def reports_page() -> rx.Component:
    content = rx.vstack(

        # ── Summary cards ─────────────────────────────────────────────
        rx.hstack(
            report_stat_card(
                "Total Assessments",
                AdminState.total_assessments,
                "clipboard-list",
                COLORS["primary"],
                COLORS["primary_soft"],
            ),
            report_stat_card(
                "Approved",
                AdminState.total_approved_assessments,
                "circle-check",
                "#027A48",
                "#ECFDF3",
            ),
            report_stat_card(
                "Awaiting Response",
                AdminState.total_pending_assessments,
                "clock",
                "#B45309",
                "#FFFBEB",
            ),
            report_stat_card(
                "Declined",
                AdminState.total_declined_assessments,
                "circle-x",
                "#991B1B",
                "#FEF2F2",
            ),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),

        # ── Assessment breakdown table ─────────────────────────────────
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.icon("bar-chart-2", size=16, color=COLORS["primary"]),
                    rx.text("Assessment Breakdown", font_family=FONT_BODY,
                            size="3", weight="bold", color=COLORS["ink"]),
                    spacing="2", align_items="center",
                ),
                rx.spacer(),
                rx.text(
                    AdminState.total_assessments.to_string() + " total records",
                    font_family=FONT_BODY, size="2", color=COLORS["slate"],
                ),
                width="100%",
                align_items="center",
                padding="1em 1.2em",
                border_bottom=f"1px solid {COLORS['line']}",
            ),
            rx.cond(
                AdminState.total_assessments == 0,
                rx.box(
                    rx.vstack(
                        rx.icon("clipboard-list", size=28, color=COLORS["slate"]),
                        rx.text("No assessments yet. Create one from the Assessments page.",
                                font_family=FONT_BODY, size="2",
                                color=COLORS["slate"], padding_top="0.6em"),
                        align_items="center",
                    ),
                    padding="3em",
                    display="flex",
                    justify_content="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Assessment"),
                            rx.table.column_header_cell("Date"),
                            rx.table.column_header_cell("Facilitator"),
                            rx.table.column_header_cell("Candidates"),
                            rx.table.column_header_cell("Tests"),
                            rx.table.column_header_cell("Status"),
                            rx.table.column_header_cell("Facilitator Response"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(AdminState.assessments, report_row),
                    ),
                    width="100%",
                ),
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            overflow="hidden",
            width="100%",
        ),

        spacing="5",
        width="100%",
        align_items="stretch",
    )

    return admin_shell(
        active="reports",
        title="Reports",
        subtitle="Assessment performance overview and facilitator response summary.",
        content=content,
    )