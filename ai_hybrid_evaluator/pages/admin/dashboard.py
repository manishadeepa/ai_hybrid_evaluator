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


def assessments_overview_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header
            rx.vstack(
                rx.text("Assessments Overview", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                rx.text("Active assessments by status", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),

            # Chart + Legend row
            rx.hstack(
                # Donut Visual
                rx.box(
                    # Outer Donut ring
                    rx.box(
                        # Cutout circle
                        rx.box(
                            rx.vstack(
                                rx.text("3", font_family=FONT_DISPLAY, size="6", weight="bold", color=COLORS["ink"], line_height="1"),
                                rx.text("Total", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="center",
                                justify_content="center",
                            ),
                            width="90px",
                            height="90px",
                            border_radius="50%",
                            background=COLORS["surface"],
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        width="140px",
                        height="140px",
                        border_radius="50%",
                        background="conic-gradient(#10B981 0% 66.7%, #F59E0B 66.7% 100%)",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        box_shadow="inset 0 0 0 1px rgba(0,0,0,0.05)",
                    ),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex="1",
                ),

                # Legend List
                rx.vstack(
                    donut_legend_item("#10B981", "In Progress", "2 (66.7%)"),
                    donut_legend_item("#F59E0B", "Awaiting Evaluation", "1 (33.3%)"),
                    donut_legend_item("#EF4444", "Completed", "0 (0%)"),
                    spacing="3",
                    align_items="start",
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
        flex="1",
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

def recent_assessment_row(
    doc_color: str,
    doc_bg: str,
    name: str,
    facilitator: str,
    candidates: str,
    tests: str,
    status_label: str,
    status_color: str,
    status_bg: str,
    last_updated: str,
) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=16, color=doc_color),
                    background=doc_bg,
                    padding="0.35em",
                    border_radius="6px",
                ),
                rx.text(name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                spacing="2",
                align_items="center",
            ),
        ),
        rx.table.cell(rx.text(facilitator, font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(rx.text(candidates, font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(rx.text(tests, font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(
            rx.badge(
                status_label,
                color_scheme=rx.cond(status_label == "In Progress", "green", "orange"),
                variant="soft",
                size="1",
                font_family=FONT_BODY,
            ),
        ),
        rx.table.cell(rx.text(last_updated, font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(
            rx.link(
                rx.hstack(
                    rx.icon("eye", size=14, color=COLORS["primary"]),
                    rx.text("View Details", font_family=FONT_BODY, size="1", weight="medium", color=COLORS["primary"]),
                    spacing="1",
                    align_items="center",
                    padding="0.3em 0.7em",
                    border=f"1px solid {COLORS['primary_light']}",
                    border_radius="6px",
                    background=COLORS["surface"],
                    _hover={"background": COLORS["primary_soft"]},
                    transition="all 0.15s ease",
                ),
                href="/admin/assessments",
                text_decoration="none",
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
                        rx.table.column_header_cell(rx.text("Tests", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Status", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Last Updated", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Action", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                    ),
                ),
                rx.table.body(
                    recent_assessment_row(
                        "#8B5CF6", "#EDE9FE", "Quality", "Ravi Kumar", "4 Candidates", "3 + Final", "In Progress", "#059669", "#ECFDF3", "31 Aug 2026, 09:45 AM"
                    ),
                    recent_assessment_row(
                        "#10B981", "#ECFDF3", "Safety", "Anitha Sharma", "6 Candidates", "3 + Final", "Awaiting Evaluation", "#D97706", "#FFFBEB", "30 Aug 2026, 04:20 PM"
                    ),
                    recent_assessment_row(
                        "#F59E0B", "#FEF3C7", "EV Systems", "Karthik Rao", "5 Candidates", "3 + Final", "In Progress", "#059669", "#ECFDF3", "30 Aug 2026, 11:10 AM"
                    ),
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
# 5. Full Admin Dashboard Page Assembly
# ─────────────────────────────────────────────────────────────

def admin_dashboard_page() -> rx.Component:
    content = rx.vstack(
        # ── Welcome Header + Date Card ────────────────────────────────
        rx.hstack(
            rx.vstack(
                rx.text(
                    "Welcome back, Admin!",
                    font_family=FONT_BODY,
                    size="6",
                    weight="bold",
                    color=COLORS["ink"],
                    line_height="1.2",
                ),
                rx.text(
                    "Here's what's happening in your evaluation system today.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.box(
                rx.hstack(
                    rx.icon("calendar", size=18, color=COLORS["slate"]),
                    rx.vstack(
                        rx.text(
                            "Monday, 31 August 2026",
                            font_family=FONT_BODY,
                            size="1",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "10:24 AM",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="10px",
                padding="0.6em 1em",
                box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.02)",
            ),
            width="100%",
            align_items="center",
            padding_bottom="0.5em",
        ),

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
                "Pending Evaluations",
                AdminState.pending_evaluations,
                "Awaiting evaluation",
                "clock",
                "#DC2626",
                "#FEF2F2",
            ),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),

        # ── 2 Visualization Cards ─────────────────────────────────────
        rx.hstack(
            assessments_overview_card(),
            evaluation_progress_card(),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),

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