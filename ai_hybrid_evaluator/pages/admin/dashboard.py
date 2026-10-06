"""
Admin dashboard overview — matches reference design with:
1. Welcome header + live date/time card
2. 4 Summary KPI stat cards
3. Assessments Overview donut chart + Evaluation Progress circular gauge
4. Recent Assessments table with colored document icons and action buttons
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────
# 1. Summary KPI Stat Card
# ─────────────────────────────────────────────────────────────

def dashboard_kpi_card(
    label: str,
    value: rx.Var,
    subtitle: str,
    icon: str,
    icon_color: str,
    icon_bg: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=24, color=icon_color),
                background=icon_bg,
                padding="0.9em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    label,
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                rx.text(
                    value,
                    font_family=FONT_DISPLAY,
                    size="6",
                    weight="bold",
                    color=COLORS["ink"],
                    line_height="1.2",
                ),
                rx.text(
                    subtitle,
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
        flex="1",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
    )


# ─────────────────────────────────────────────────────────────
# 2. Donut Chart Component (CSS / SVG)
# ─────────────────────────────────────────────────────────────

def donut_legend_item(color: str, label: str, count_pct: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            width="9px",
            height="9px",
            border_radius="50%",
            background=color,
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(label, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
            rx.text(count_pct, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
            spacing="0",
            align_items="start",
        ),
        spacing="2",
        align_items="start",
    )


def assessment_donut_svg() -> rx.Component:
    return rx.html(AdminState.assessment_donut_svg_html)


def status_overview_card(
    dot_color: str,
    title: str,
    count: rx.Var | str,
    subtitle: rx.Var | str,
    card_bg: str,
    card_border: str,
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    width="10px",
                    height="10px",
                    border_radius="50%",
                    background=dot_color,
                    flex_shrink="0",
                ),
                rx.text(
                    title,
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    count,
                    font_family=FONT_DISPLAY,
                    size="7",
                    weight="bold",
                    color=COLORS["ink"],
                    line_height="1",
                ),
                rx.text(
                    subtitle,
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        background=card_bg,
        border=f"1px solid {card_border}",
        border_radius="12px",
        padding="1.2em 1.3em",
        flex="1",
    )


def assessments_overview_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header
            rx.vstack(
                rx.text("Assessment Overview", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                rx.text("Current assessment status", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),

            # Chart + 3 Status Cards row
            rx.hstack(
                # Donut Visual
                rx.box(
                    assessment_donut_svg(),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    padding_x="1.5em",
                    flex_shrink="0",
                ),

                # 3 Status Cards
                rx.hstack(
                    status_overview_card(
                        dot_color="#10B981",
                        title="In Progress",
                        count=AdminState.assessment_in_progress_count.to_string(),
                        subtitle=AdminState.assessment_in_progress_pct_subtitle,
                        card_bg="#ECFDF5",
                        card_border="#D1FAE5",
                    ),
                    status_overview_card(
                        dot_color="#F59E0B",
                        title="Pending",
                        count=AdminState.assessment_pending_count.to_string(),
                        subtitle=AdminState.assessment_pending_pct_subtitle,
                        card_bg="#FFFBEB",
                        card_border="#FEF3C7",
                    ),
                    status_overview_card(
                        dot_color="#2563EB",
                        title="Completed",
                        count=AdminState.assessment_completed_count.to_string(),
                        subtitle=AdminState.assessment_completed_pct_subtitle,
                        card_bg="#EFF6FF",
                        card_border="#DBEAFE",
                    ),
                    spacing="4",
                    align_items="stretch",
                    flex="1",
                ),
                spacing="4",
                align_items="center",
                width="100%",
                padding_y="1em",
            ),

            rx.spacer(),

            # Bottom CTA button
            rx.hstack(
                rx.link(
                    rx.hstack(
                        rx.text("View All Assessments", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["primary"]),
                        rx.icon("chevron-right", size=14, color=COLORS["primary"]),
                        spacing="1",
                        align_items="center",
                        justify_content="center",
                        padding="0.5em 1.2em",
                        border=f"1px solid {COLORS['primary_light']}",
                        border_radius="8px",
                        background=COLORS["surface"],
                        _hover={"background": COLORS["primary_soft"]},
                        transition="all 0.15s ease",
                    ),
                    href="/admin/assessments",
                    text_decoration="none",
                ),
                width="100%",
                justify_content="center",
                padding_top="0.5em",
            ),
            spacing="3",
            width="100%",
            height="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        width="100%",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
    )



# ─────────────────────────────────────────────────────────────
# 3. Circular Completion Gauge Card
# ─────────────────────────────────────────────────────────────

def evaluation_progress_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header
            rx.vstack(
                rx.text("Evaluation Progress", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                rx.text("Overall evaluation completion rate", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),

            # Visual Gauge + Mini Cards
            rx.hstack(
                # Gauge
                rx.box(
                    rx.box(
                        rx.box(
                            rx.vstack(
                                rx.text("70%", font_family=FONT_DISPLAY, size="6", weight="bold", color=COLORS["primary"], line_height="1"),
                                rx.text("Completed", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="center",
                                justify_content="center",
                            ),
                            width="100px",
                            height="100px",
                            border_radius="50%",
                            background=COLORS["surface"],
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        width="140px",
                        height="140px",
                        border_radius="50%",
                        background="conic-gradient(#6D28D9 0% 70%, #E2E8F0 70% 100%)",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex="1",
                ),

                # Mini KPI Cards
                rx.vstack(
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("trending-up", size=18, color="#6D28D9"),
                                background="#EDE9FE",
                                padding="0.4em",
                                border_radius="6px",
                            ),
                            rx.vstack(
                                rx.text("Evaluations Completed", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.text("7 / 10", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#F5F3FF",
                        border="1px solid #EDE9FE",
                        border_radius="8px",
                        padding="0.6em 0.9em",
                        width="100%",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("clock", size=18, color="#D97706"),
                                background="#FEF3C7",
                                padding="0.4em",
                                border_radius="6px",
                            ),
                            rx.vstack(
                                rx.text("Pending Evaluations", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.text("3", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        background="#FFFBEB",
                        border="1px solid #FEF3C7",
                        border_radius="8px",
                        padding="0.6em 0.9em",
                        width="100%",
                    ),
                    spacing="2",
                    align_items="stretch",
                    flex="1",
                ),
                spacing="4",
                align_items="center",
                width="100%",
                padding_y="1em",
            ),

            rx.spacer(),

            # Bottom CTA button
            rx.hstack(
                rx.link(
                    rx.hstack(
                        rx.text("View Pending Evaluations", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["primary"]),
                        rx.icon("chevron-right", size=14, color=COLORS["primary"]),
                        spacing="1",
                        align_items="center",
                        justify_content="center",
                        padding="0.5em 1.2em",
                        border=f"1px solid {COLORS['primary_light']}",
                        border_radius="8px",
                        background=COLORS["surface"],
                        _hover={"background": COLORS["primary_soft"]},
                        transition="all 0.15s ease",
                    ),
                    href="/admin/reports",
                    text_decoration="none",
                ),
                width="100%",
                justify_content="center",
                padding_top="0.5em",
            ),
            spacing="3",
            width="100%",
            height="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        flex="1",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
    )


# ─────────────────────────────────────────────────────────────
# 4. Recent Assessments Table
# ─────────────────────────────────────────────────────────────

def recent_assessment_row(assessment) -> rx.Component:
    """Render one persisted assessment in the dashboard."""

    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.icon(
                        "file-text",
                        size=16,
                        color=COLORS["primary"],
                    ),
                    background=COLORS["primary_soft"],
                    padding="0.35em",
                    border_radius="6px",
                ),
                rx.text(
                    assessment["name"],
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
                rx.cond(assessment["facilitator_names"].length() > 0,
                            assessment["facilitator_names"].join(", "), assessment["facilitator_name"]),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
        ),

        rx.table.cell(
            rx.text(
                assessment["assigned_candidates"].length().to_string()
                + " Candidates",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
        ),

        rx.table.cell(
            rx.text(
                assessment["tests"].length().to_string()
                + " Tests",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
        ),

        rx.table.cell(
            rx.badge(
                assessment["status"],
                color_scheme=rx.cond(
                    assessment["status"] == "Completed",
                    "green",
                    rx.cond(
                        assessment["status"] == "Active",
                        "blue",
                        "orange",
                    ),
                ),
                variant="soft",
                size="1",
                font_family=FONT_BODY,
            ),
        ),

        rx.table.cell(
            rx.link(
                rx.hstack(
                    rx.icon(
                        "eye",
                        size=14,
                        color=COLORS["primary"],
                    ),
                    rx.text(
                        "View Details",
                        font_family=FONT_BODY,
                        size="1",
                        weight="medium",
                        color=COLORS["primary"],
                    ),
                    spacing="1",
                    align_items="center",
                    padding="0.3em 0.7em",
                    border=f"1px solid {COLORS['primary_light']}",
                    border_radius="6px",
                    background=COLORS["surface"],
                    _hover={
                        "background": COLORS["primary_soft"]
                    },
                    transition="all 0.15s ease",
                ),
                href="/admin/assessments",
                text_decoration="none",
            ),
        ),
    )


def recent_assessments_card() -> rx.Component:
    """Dashboard table backed by persisted assessments."""

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Recent Assessments",
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Latest assessments activity",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                width="100%",
                padding_bottom="0.8em",
            ),

            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            "Assessment Name"
                        ),
                        rx.table.column_header_cell(
                            "Facilitator"
                        ),
                        rx.table.column_header_cell(
                            "Candidates"
                        ),
                        rx.table.column_header_cell(
                            "Tests"
                        ),
                        rx.table.column_header_cell(
                            "Status"
                        ),
                        rx.table.column_header_cell(
                            "Action"
                        ),
                    ),
                ),

                rx.table.body(
                    rx.foreach(
                        AdminState.assessments,
                        recent_assessment_row,
                    )
                ),

                width="100%",
            ),

            rx.hstack(
                rx.link(
                    rx.hstack(
                        rx.text(
                            "View All Assessments",
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color=COLORS["primary"],
                        ),
                        rx.icon(
                            "chevron-right",
                            size=14,
                            color=COLORS["primary"],
                        ),
                        spacing="1",
                        align_items="center",
                        justify_content="center",
                        padding="0.5em 1.2em",
                        border=(
                            f"1px solid "
                            f"{COLORS['primary_light']}"
                        ),
                        border_radius="8px",
                        background=COLORS["surface"],
                        _hover={
                            "background": COLORS["primary_soft"]
                        },
                        transition="all 0.15s ease",
                    ),
                    href="/admin/assessments",
                    text_decoration="none",
                ),
                justify="center",
                width="100%",
                padding_top="0.8em",
            ),

            spacing="0",
            width="100%",
            align_items="stretch",
        ),

        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        width="100%",
    )


# 5. Full Admin Dashboard Page Assembly
# ─────────────────────────────────────────────────────────────

def admin_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # ── 4 KPI Stat Cards ──────────────────────────────────────────
        rx.hstack(
            dashboard_kpi_card(
                "Total Facilitators",
                AdminState.total_facilitators,
                "Active facilitators",
                "users",
                "#6D28D9",
                "#EDE9FE",
            ),
            dashboard_kpi_card(
                "Total Candidates",
                AdminState.total_candidates,
                "Registered candidates",
                "user",
                "#059669",
                "#ECFDF3",
            ),
            dashboard_kpi_card(
                "Active Assessments",
                AdminState.active_assessments,
                "Currently running",
                "clipboard-list",
                "#D97706",
                "#FEF3C7",
            ),
            dashboard_kpi_card(
                "Completed Assessments",
                AdminState.completed_assessments,
                "Successfully completed",
                "circle-check",
                "#2563EB",
                "#DBEAFE",
            ),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),

        # ── Assessment Overview (expanded) ───────────────────────────
        assessments_overview_card(),

        # ── Recent Assessments Table ──────────────────────────────────
        recent_assessments_card(),

        spacing="5",
        width="100%",
        align_items="stretch",
    )

    return admin_shell(
        active="dashboard",
        title="Dashboard",
        subtitle="Overview of facilitators, candidates, and assessments.",
        content=content,
    )
