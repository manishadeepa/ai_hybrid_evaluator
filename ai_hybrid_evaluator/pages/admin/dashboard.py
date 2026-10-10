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
# 2. Donut Chart & Status Cards Component
# ─────────────────────────────────────────────────────────────

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
                rx.text("Current facilitator approval and assessment closure status", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
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
                        count=AdminState.dashboard_assessments_in_progress_count.to_string(),
                        subtitle=AdminState.dashboard_assessments_in_progress_subtitle,
                        card_bg="#ECFDF5",
                        card_border="#D1FAE5",
                    ),
                    status_overview_card(
                        dot_color="#F59E0B",
                        title="Pending",
                        count=AdminState.dashboard_assessments_pending_count.to_string(),
                        subtitle=AdminState.dashboard_assessments_pending_subtitle,
                        card_bg="#FFFBEB",
                        card_border="#FEF3C7",
                    ),
                    status_overview_card(
                        dot_color="#2563EB",
                        title="Completed",
                        count=AdminState.dashboard_assessments_completed_count.to_string(),
                        subtitle=AdminState.dashboard_assessments_completed_subtitle,
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
# 3. Recent Assessments Table
# ─────────────────────────────────────────────────────────────

def recent_assessment_row(a: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=16, color="#8B5CF6"),
                    background="#EDE9FE",
                    padding="0.35em",
                    border_radius="6px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(a["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                spacing="2",
                align_items="center",
            ),
        ),
        rx.table.cell(
            rx.cond(
                a["facilitator_names"].length() > 0,
                rx.text(a["facilitator_names"].join(", "), font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                rx.text(a["facilitator_name"], font_family=FONT_BODY, size="2", color=COLORS["slate"]),
            ),
        ),
        rx.table.cell(
            rx.text(
                a["assigned_candidates"].length().to_string() + " Candidates",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
        ),
    )


def recent_assessments_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Recent Assessments", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                    rx.text("Latest assessments activity", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                width="100%",
                padding_bottom="0.8em",
            ),

            # Table
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(rx.text("Assessment Name", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Facilitator", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Candidates", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AdminState.assessments, recent_assessment_row)
                ),
                width="100%",
            ),

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
                padding_top="1.2em",
            ),
            spacing="3",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.4em",
        width="100%",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
    )


# ─────────────────────────────────────────────────────────────
# 4. Full Admin Dashboard Page Assembly
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
