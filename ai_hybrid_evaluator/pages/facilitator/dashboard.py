"""
Facilitator Dashboard — matches TVS reference design with:
1. Single summary KPI stat card: Total Assessments (clickable -> All Assessments modal)
2. Two Donut Charts side-by-side:
   - Candidate Test Completion (with assessment dropdown & clickable segments/legend)
   - Evaluation Status (with assessment dropdown & clickable segments/legend)
3. Assessment Overview table below charts (exact 6 columns, no Action column)
4. Modals for all breakdowns matching TVS theme
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────
# 1. Total Assessments KPI Card
# ─────────────────────────────────────────────────────────────

def total_assessments_kpi_card() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("file-text", size=24, color="#6D28D9"),
                background="#EDE9FE",
                padding="0.9em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    "Total Assessments",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                rx.text(
                    FacilitatorState.my_assessments.length().to_string(),
                    font_family=FONT_DISPLAY,
                    size="6",
                    weight="bold",
                    color=COLORS["ink"],
                    line_height="1.2",
                ),
                rx.text(
                    "Assessments assigned",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="0",
                align_items="start",
            ),
            spacing="4",
            align_items="center",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.2em 1.4em",
        width="100%",
        max_width="340px",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
        cursor="pointer",
        on_click=FacilitatorState.open_all_assessments_modal,
        _hover={
            "box_shadow": "0 4px 14px rgba(109, 40, 217, 0.12)",
            "border_color": "#6D28D9",
            "transform": "translateY(-1px)",
        },
        transition="all 0.15s ease",
    )


# ─────────────────────────────────────────────────────────────
# 2. Donut Chart Helpers & SVG
# ─────────────────────────────────────────────────────────────

def _completion_segment_slice(seg: dict) -> rx.Component:
    return rx.el.g(
        rx.cond(
            seg["d"] != "",
            rx.fragment(
                rx.el.path(
                    d=seg["d"],
                    fill=seg["fill"],
                    stroke="#ffffff",
                    stroke_width="1.5",
                ),
                rx.cond(
                    seg["label"] != "",
                    rx.el.text(
                        seg["label"],
                        x=seg["tx"],
                        y=seg["ty"],
                        text_anchor="middle",
                        dominant_baseline="central",
                        fill="#ffffff",
                        font_size="13",
                        font_weight="700",
                        font_family="Inter, system-ui, sans-serif",
                        style={"textShadow": "0 1px 2px rgba(0,0,0,0.35)", "pointerEvents": "none"},
                    ),
                    rx.fragment(),
                ),
            ),
            rx.fragment(),
        ),
        on_click=FacilitatorState.open_completion_breakdown_modal(seg["name"]),
        cursor="pointer",
        _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
        transition="all 0.15s ease",
    )


def candidate_completion_donut_svg() -> rx.Component:
    return rx.el.svg(
        rx.el.g(
            rx.foreach(FacilitatorState.candidate_completion_donut_segments, _completion_segment_slice),
            # Center circular cutout
            rx.el.circle(
                cx="100",
                cy="100",
                r="53",
                fill="#ffffff",
            ),
            rx.el.text(
                FacilitatorState.candidate_completion_total_count.to_string(),
                x="100",
                y="85",
                text_anchor="middle",
                dominant_baseline="central",
                fill="#0F172A",
                font_size="28",
                font_weight="700",
                font_family="Plus Jakarta Sans, system-ui, sans-serif",
                style={"pointerEvents": "none"},
            ),
            rx.el.text(
                "Total",
                x="100",
                y="106",
                text_anchor="middle",
                dominant_baseline="central",
                fill="#64748B",
                font_size="11",
                font_weight="500",
                font_family="Inter, system-ui, sans-serif",
                style={"pointerEvents": "none"},
            ),
        ),
        width="190",
        height="190",
        view_box="0 0 200 200",
        xmlns="http://www.w3.org/2000/svg",
        style={"display": "block", "maxWidth": "100%", "height": "auto"},
    )


def _evaluation_segment_slice(seg: dict) -> rx.Component:
    return rx.el.g(
        rx.cond(
            seg["d"] != "",
            rx.fragment(
                rx.el.path(
                    d=seg["d"],
                    fill=seg["fill"],
                    stroke="#ffffff",
                    stroke_width="1.5",
                ),
                rx.cond(
                    seg["label"] != "",
                    rx.el.text(
                        seg["label"],
                        x=seg["tx"],
                        y=seg["ty"],
                        text_anchor="middle",
                        dominant_baseline="central",
                        fill="#ffffff",
                        font_size="13",
                        font_weight="700",
                        font_family="Inter, system-ui, sans-serif",
                        style={"textShadow": "0 1px 2px rgba(0,0,0,0.35)", "pointerEvents": "none"},
                    ),
                    rx.fragment(),
                ),
            ),
            rx.fragment(),
        ),
        on_click=FacilitatorState.open_evaluation_breakdown_modal(seg["name"]),
        cursor="pointer",
        _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
        transition="all 0.15s ease",
    )


def evaluation_status_donut_svg() -> rx.Component:
    return rx.el.svg(
        rx.el.g(
            rx.foreach(FacilitatorState.evaluation_status_donut_segments, _evaluation_segment_slice),
            # Center circular cutout
            rx.el.circle(
                cx="100",
                cy="100",
                r="53",
                fill="#ffffff",
            ),
            rx.el.text(
                FacilitatorState.evaluation_status_total_count.to_string(),
                x="100",
                y="85",
                text_anchor="middle",
                dominant_baseline="central",
                fill="#0F172A",
                font_size="28",
                font_weight="700",
                font_family="Plus Jakarta Sans, system-ui, sans-serif",
                style={"pointerEvents": "none"},
            ),
            rx.el.text(
                "Evaluations",
                x="100",
                y="106",
                text_anchor="middle",
                dominant_baseline="central",
                fill="#64748B",
                font_size="11",
                font_weight="500",
                font_family="Inter, system-ui, sans-serif",
                style={"pointerEvents": "none"},
            ),
        ),
        width="220",
        height="220",
        view_box="0 0 200 200",
        xmlns="http://www.w3.org/2000/svg",
        style={"display": "block", "maxWidth": "100%", "height": "auto"},
    )


# ─────────────────────────────────────────────────────────────
# 3. Chart Cards (Side-by-Side)
# ─────────────────────────────────────────────────────────────

def candidate_completion_chart_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Card Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Candidate Test Completion",
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Completion status of candidate tests for the selected assessment.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                    flex="1",
                ),
                rx.select(
                    FacilitatorState.dashboard_assessment_names,
                    value=FacilitatorState.effective_completion_assessment_name,
                    on_change=FacilitatorState.set_dashboard_completion_assessment_name,
                    size="2",
                    variant="surface",
                    radius="medium",
                    min_width="120px",
                    max_width="180px",
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.6em",
            ),
            # Donut & Legend
            rx.vstack(
                candidate_completion_donut_svg(),
                rx.hstack(
                    # Completed Legend Item
                    rx.box(
                        rx.hstack(
                            rx.box(width="8px", height="8px", border_radius="50%", background="#10B981", flex_shrink="0"),
                            rx.text("Completed:", font_family=FONT_BODY, size="2", color="#1E293B", weight="medium"),
                            rx.text(FacilitatorState.candidate_completion_completed_count.to_string(), font_family=FONT_BODY, size="2", color="#10B981", weight="bold"),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#ECFDF5",
                        border="1px solid #D1FAE5",
                        border_radius="8px",
                        padding="0.45em 0.85em",
                        cursor="pointer",
                        on_click=FacilitatorState.open_completion_breakdown_modal("Completed"),
                        _hover={"background": "#D1FAE5", "transform": "scale(1.02)"},
                        transition="all 0.15s ease",
                    ),
                    # Not Completed Legend Item
                    rx.box(
                        rx.hstack(
                            rx.box(width="8px", height="8px", border_radius="50%", background="#F59E0B", flex_shrink="0"),
                            rx.text("Not Completed:", font_family=FONT_BODY, size="2", color="#1E293B", weight="medium"),
                            rx.text(FacilitatorState.candidate_completion_not_completed_count.to_string(), font_family=FONT_BODY, size="2", color="#D97706", weight="bold"),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#FFFBEB",
                        border="1px solid #FEF3C7",
                        border_radius="8px",
                        padding="0.45em 0.85em",
                        cursor="pointer",
                        on_click=FacilitatorState.open_completion_breakdown_modal("Not Completed"),
                        _hover={"background": "#FEF3C7", "transform": "scale(1.02)"},
                        transition="all 0.15s ease",
                    ),
                    spacing="3",
                    justify_content="center",
                    width="100%",
                    padding_top="0.4em",
                ),
                align_items="center",
                width="100%",
                spacing="2",
            ),
            spacing="3",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.3em 1.5em",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
        flex="1",
        width="100%",
        min_width="0",  # allow card to shrink inside CSS grid cell
    )


def evaluation_status_chart_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Card Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Evaluation Status",
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Evaluation progress for submitted candidate tests for the selected assessment.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                    flex="1",
                ),
                rx.select(
                    FacilitatorState.dashboard_assessment_names,
                    value=FacilitatorState.effective_evaluation_assessment_name,
                    on_change=FacilitatorState.set_dashboard_evaluation_assessment_name,
                    size="2",
                    variant="surface",
                    radius="medium",
                    min_width="120px",
                    max_width="180px",
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.6em",
            ),
            # Donut & Legend
            rx.vstack(
                evaluation_status_donut_svg(),
                rx.hstack(
                    # Evaluations Completed Legend Item
                    rx.box(
                        rx.hstack(
                            rx.box(width="8px", height="8px", border_radius="50%", background="#10B981", flex_shrink="0"),
                            rx.text("Evaluations Completed:", font_family=FONT_BODY, size="2", color="#1E293B", weight="medium"),
                            rx.text(FacilitatorState.evaluation_status_completed_count.to_string(), font_family=FONT_BODY, size="2", color="#10B981", weight="bold"),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#ECFDF5",
                        border="1px solid #D1FAE5",
                        border_radius="8px",
                        padding="0.45em 0.85em",
                        cursor="pointer",
                        on_click=FacilitatorState.open_evaluation_breakdown_modal("Evaluations Completed"),
                        _hover={"background": "#D1FAE5", "transform": "scale(1.02)"},
                        transition="all 0.15s ease",
                    ),
                    # Pending Evaluations Legend Item
                    rx.box(
                        rx.hstack(
                            rx.box(width="8px", height="8px", border_radius="50%", background="#F59E0B", flex_shrink="0"),
                            rx.text("Pending Evaluations:", font_family=FONT_BODY, size="2", color="#1E293B", weight="medium"),
                            rx.text(FacilitatorState.evaluation_status_pending_count.to_string(), font_family=FONT_BODY, size="2", color="#D97706", weight="bold"),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#FFFBEB",
                        border="1px solid #FEF3C7",
                        border_radius="8px",
                        padding="0.45em 0.85em",
                        cursor="pointer",
                        on_click=FacilitatorState.open_evaluation_breakdown_modal("Pending Evaluations"),
                        _hover={"background": "#FEF3C7", "transform": "scale(1.02)"},
                        transition="all 0.15s ease",
                    ),
                    spacing="3",
                    justify_content="center",
                    width="100%",
                    padding_top="0.4em",
                ),
                align_items="center",
                width="100%",
                spacing="2",
            ),
            spacing="3",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.3em 1.5em",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
        flex="1",
        width="100%",
        min_width="0",  # allow card to shrink inside CSS grid cell
    )


def assessment_collaboration_card() -> rx.Component:
    """Card displaying assigned facilitators and recent test activity for the selected assessment."""
    return rx.box(
        rx.vstack(
            # Card Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Assessment Collaboration & Activity",
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Facilitators working on this assessment and their recent activity.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                    flex="1",
                ),
                rx.select(
                    FacilitatorState.dashboard_assessment_names,
                    value=FacilitatorState.effective_collaboration_assessment_name,
                    on_change=FacilitatorState.set_dashboard_collaboration_assessment_name,
                    size="2",
                    variant="surface",
                    radius="medium",
                    min_width="120px",
                    max_width="180px",
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.6em",
            ),

            # Assigned Facilitators Section
            rx.vstack(
                rx.hstack(
                    rx.text("Assigned Facilitators (", font_family=FONT_BODY, font_size="0.75rem", font_weight="bold", color="#64748B"),
                    rx.text(FacilitatorState.collaboration_assigned_count.to_string(), font_family=FONT_BODY, font_size="0.75rem", font_weight="bold", color="#64748B"),
                    rx.text(")", font_family=FONT_BODY, font_size="0.75rem", font_weight="bold", color="#64748B"),
                    spacing="0",
                    align_items="center",
                ),
                rx.hstack(
                    rx.foreach(
                        FacilitatorState.collaboration_assigned_facilitators,
                        lambda fac: rx.hstack(
                            rx.box(
                                rx.text(
                                    fac["initial"],
                                    font_family=FONT_DISPLAY,
                                    font_weight="bold",
                                    font_size="0.8rem",
                                    color=fac["text"],
                                ),
                                width="32px",
                                height="32px",
                                border_radius="50%",
                                background=fac["bg"],
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                flex_shrink="0",
                            ),
                            rx.vstack(
                                rx.text(
                                    fac["name"],
                                    font_family=FONT_BODY,
                                    font_size="0.8rem",
                                    font_weight="bold",
                                    color="#0F172A",
                                    line_height="1.2",
                                ),
                                rx.text(
                                    fac["role"],
                                    font_family=FONT_BODY,
                                    font_size="0.68rem",
                                    color="#64748B",
                                    line_height="1.2",
                                ),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="2",
                            align_items="center",
                            padding_right="0.8em",
                        ),
                    ),
                    spacing="3",
                    align_items="center",
                    flex_wrap="wrap",
                ),
                spacing="2",
                align_items="start",
                width="100%",
                padding_bottom="0.4em",
            ),

            # Table of Test Activity
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("#", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B", width="28px"),
                            rx.table.column_header_cell("Test", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B"),
                            rx.table.column_header_cell("Evaluation Status", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B"),
                            rx.table.column_header_cell("Evaluated By", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B"),
                            rx.table.column_header_cell("Test Lock Status", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B"),
                            rx.table.column_header_cell("Locked By", font_family=FONT_BODY, font_size="0.72rem", font_weight="bold", color="#64748B"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            FacilitatorState.collaboration_test_activity,
                            lambda row: rx.table.row(
                                rx.table.cell(rx.text(row["index"], font_family=FONT_BODY, font_size="0.75rem", color="#64748B")),
                                rx.table.cell(rx.text(row["test_name"], font_family=FONT_BODY, font_size="0.78rem", font_weight="bold", color="#0F172A")),
                                rx.table.cell(
                                    rx.badge(
                                        row["evaluation_status"],
                                        color_scheme=row["status_color"],
                                        variant="soft",
                                        size="1",
                                        radius="full",
                                        font_weight="600",
                                        font_size="0.7rem",
                                        padding="0.15em 0.6em",
                                    ),
                                ),
                                rx.table.cell(rx.text(row["evaluated_by"], font_family=FONT_BODY, font_size="0.75rem", color="#334155", font_weight="medium")),
                                rx.table.cell(
                                    rx.cond(
                                        row["lock_status"] == "Locked",
                                        rx.badge(
                                            rx.hstack(
                                                rx.icon("lock", size=10),
                                                rx.text("Locked", font_size="0.7rem"),
                                                spacing="1",
                                                align_items="center",
                                            ),
                                            color_scheme="green",
                                            variant="soft",
                                            size="1",
                                            radius="full",
                                            font_weight="600",
                                            padding="0.15em 0.6em",
                                        ),
                                        rx.badge(
                                            rx.hstack(
                                                rx.icon("lock-open", size=10),
                                                rx.text("Unlocked", font_size="0.7rem"),
                                                spacing="1",
                                                align_items="center",
                                            ),
                                            color_scheme="gray",
                                            variant="soft",
                                            size="1",
                                            radius="full",
                                            font_weight="500",
                                            padding="0.15em 0.6em",
                                        ),
                                    ),
                                ),
                                rx.table.cell(rx.text(row["locked_by"], font_family=FONT_BODY, font_size="0.75rem", color="#334155", font_weight="medium")),
                                _hover={"background": "#F8FAFC"},
                            ),
                        ),
                    ),
                    width="100%",
                    variant="surface",
                    size="1",
                ),
                border="1px solid #E2E8F0",
                border_radius="10px",
                overflow="hidden",
                width="100%",
                max_height="220px",
                overflow_y="auto",
                overflow_x="auto",  # let the table scroll horizontally inside the card
            ),
            spacing="3",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.3em 1.5em",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
        flex="1",
        width="100%",
        min_width="0",  # allow card to shrink inside CSS grid cell
    )


# ─────────────────────────────────────────────────────────────
# 4. Assessment Overview Table
# ─────────────────────────────────────────────────────────────

def _overview_table_row(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.icon("clipboard-check", size=15, color=COLORS["primary"]),
                    background=COLORS["primary_soft"],
                    padding="0.4em",
                    border_radius="6px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                rx.text(
                    item["assessment_name"],
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                item["total_tests"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                weight="medium",
                text_align="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                item["candidate_tests_completed"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color="#059669",
                weight="bold",
                text_align="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                item["not_completed"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color="#D97706",
                weight="bold",
                text_align="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                item["pending_evaluations"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color="#D97706",
                weight="bold",
                text_align="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                item["evaluations_completed"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color="#059669",
                weight="bold",
                text_align="center",
            ),
        ),
        _hover={"background": "#F8FAFC"},
        transition="background 0.15s ease",
    )


def assessment_overview_section() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Section Header with Search
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Assessment Overview",
                        font_family=FONT_DISPLAY,
                        size="4",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Detailed progress metrics across all your assigned assessments.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.box(
                    rx.input(
                        rx.input.slot(rx.icon("search", size=15, color=COLORS["slate"])),
                        placeholder="Search assessments...",
                        value=FacilitatorState.dashboard_overview_search,
                        on_change=FacilitatorState.set_dashboard_overview_search,
                        size="2",
                        width="260px",
                        font_family=FONT_BODY,
                        border_radius="8px",
                    ),
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.8em",
            ),
            # Table
            rx.box(
                rx.cond(
                    FacilitatorState.filtered_dashboard_overview.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Assessment Name"),
                                rx.table.column_header_cell("Total Tests", text_align="center"),
                                rx.table.column_header_cell("Candidate Tests Completed", text_align="center"),
                                rx.table.column_header_cell("Not Completed", text_align="center"),
                                rx.table.column_header_cell("Pending Evaluations", text_align="center"),
                                rx.table.column_header_cell("Evaluations Completed", text_align="center"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(FacilitatorState.filtered_dashboard_overview, _overview_table_row),
                        ),
                        width="100%",
                        variant="surface",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.icon("search-x", size=24, color=COLORS["slate"]),
                            rx.text("No assessments match your search.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                            align_items="center",
                            padding="2.5em",
                        ),
                        width="100%",
                    ),
                ),
                width="100%",
                overflow_x="auto",
            ),
            spacing="3",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.5em",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────
# 5. Modals
# ─────────────────────────────────────────────────────────────

def all_assessments_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-text", size=20, color="#6D28D9"),
                            background="#EDE9FE",
                            padding="0.6em",
                            border_radius="10px",
                        ),
                        rx.vstack(
                            rx.text(
                                "All Assessments",
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Assessments assigned to you",
                                font_family=FONT_BODY,
                                size="1",
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
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),
                # Modal Table
                rx.box(
                    rx.cond(
                        FacilitatorState.all_assessments_modal_items.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("#", width="60px"),
                                    rx.table.column_header_cell("Assessment Name"),
                                    rx.table.column_header_cell("Total Tests", text_align="right"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    FacilitatorState.all_assessments_modal_items,
                                    lambda item: rx.table.row(
                                        rx.table.cell(rx.text(item["index"], font_family=FONT_BODY, size="2", color=COLORS["slate"], weight="medium")),
                                        rx.table.cell(rx.text(item["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                        rx.table.cell(rx.text(item["total_tests"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["primary"], text_align="right")),
                                        _hover={"background": "#F8FAFC"},
                                    ),
                                ),
                            ),
                            width="100%",
                            variant="surface",
                        ),
                        rx.box(
                            rx.text("No assessments assigned.", font_family=FONT_BODY, size="2", color=COLORS["slate"], text_align="center"),
                            padding="2em",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    max_height="400px",
                    overflow_y="auto",
                    padding_top="0.5em",
                ),
                spacing="3",
                width="100%",
            ),
            max_width="520px",
            border_radius="14px",
            padding="1.5em",
            background=COLORS["surface"],
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=FacilitatorState.show_all_assessments_modal,
        on_open_change=FacilitatorState.set_show_all_assessments_modal,
    )


def completion_breakdown_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("pie-chart", size=20, color="#6D28D9"),
                            background="#EDE9FE",
                            padding="0.6em",
                            border_radius="10px",
                        ),
                        rx.vstack(
                            rx.text(
                                FacilitatorState.completion_modal_title,
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Test-wise breakdown for selected assessment",
                                font_family=FONT_BODY,
                                size="1",
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
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),
                # Modal Table
                rx.box(
                    rx.cond(
                        FacilitatorState.completion_modal_items.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("#", width="60px"),
                                    rx.table.column_header_cell("Test Name"),
                                    rx.table.column_header_cell(FacilitatorState.completion_modal_col_name, text_align="right"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    FacilitatorState.completion_modal_items,
                                    lambda item: rx.table.row(
                                        rx.table.cell(rx.text(item["index"], font_family=FONT_BODY, size="2", color=COLORS["slate"], weight="medium")),
                                        rx.table.cell(rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                        rx.table.cell(rx.text(item["count"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], text_align="right")),
                                        _hover={"background": "#F8FAFC"},
                                    ),
                                ),
                            ),
                            width="100%",
                            variant="surface",
                        ),
                        rx.box(
                            rx.text("No test records found for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], text_align="center"),
                            padding="2em",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    max_height="400px",
                    overflow_y="auto",
                    padding_top="0.5em",
                ),
                spacing="3",
                width="100%",
            ),
            max_width="560px",
            border_radius="14px",
            padding="1.5em",
            background=COLORS["surface"],
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=FacilitatorState.show_completion_breakdown_modal,
        on_open_change=FacilitatorState.set_show_completion_breakdown_modal,
    )


def evaluation_breakdown_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("circle-check", size=20, color="#6D28D9"),
                            background="#EDE9FE",
                            padding="0.6em",
                            border_radius="10px",
                        ),
                        rx.vstack(
                            rx.text(
                                FacilitatorState.evaluation_modal_title,
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "Test-wise breakdown for selected assessment",
                                font_family=FONT_BODY,
                                size="1",
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
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),
                # Modal Table
                rx.box(
                    rx.cond(
                        FacilitatorState.evaluation_modal_items.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("#", width="60px"),
                                    rx.table.column_header_cell("Test Name"),
                                    rx.table.column_header_cell(FacilitatorState.evaluation_modal_col_name, text_align="right"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    FacilitatorState.evaluation_modal_items,
                                    lambda item: rx.table.row(
                                        rx.table.cell(rx.text(item["index"], font_family=FONT_BODY, size="2", color=COLORS["slate"], weight="medium")),
                                        rx.table.cell(rx.text(item["test_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                        rx.table.cell(rx.text(item["count"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], text_align="right")),
                                        _hover={"background": "#F8FAFC"},
                                    ),
                                ),
                            ),
                            width="100%",
                            variant="surface",
                        ),
                        rx.box(
                            rx.text("No test records found for this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], text_align="center"),
                            padding="2em",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    max_height="400px",
                    overflow_y="auto",
                    padding_top="0.5em",
                ),
                spacing="3",
                width="100%",
            ),
            max_width="560px",
            border_radius="14px",
            padding="1.5em",
            background=COLORS["surface"],
            box_shadow="0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        ),
        open=FacilitatorState.show_evaluation_breakdown_modal,
        on_open_change=FacilitatorState.set_show_evaluation_breakdown_modal,
    )


# ─────────────────────────────────────────────────────────────
# 6. Page Root
# ─────────────────────────────────────────────────────────────

def facilitator_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # 1. KPI Stat Card: Total Assessments
        total_assessments_kpi_card(),

        # 2. Side-by-Side Donut Charts & Collaboration Row
        rx.grid(
            candidate_completion_chart_card(),
            evaluation_status_chart_card(),
            assessment_collaboration_card(),
            # On desktop (≥1024 px) show all 3 cards in one row;
            # stack vertically only on smaller screens.
            columns=rx.breakpoints(initial="1", md="1", lg="3"),
            spacing="4",
            width="100%",
            align="stretch",  # give each card the same row height
        ),

        # 3. Assessment Overview Table
        assessment_overview_section(),

        # 4. Modals
        all_assessments_modal(),
        completion_breakdown_modal(),
        evaluation_breakdown_modal(),

        spacing="5",
        width="100%",
        align_items="stretch",
    )
    return facilitator_shell(
        active="dashboard",
        title="Dashboard",
        subtitle="Overview of your assigned assessments and evaluation progress.",
        content=content,
    )