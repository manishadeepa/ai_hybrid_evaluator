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

def _donut_segment_slice(seg: dict) -> rx.Component:
    return rx.el.g(
        rx.el.path(
            d=seg["d"],
            fill=seg["fill"],
            stroke="#ffffff",
            stroke_width="1.5",
        ),
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
        on_click=AdminState.open_assessment_overview_modal(seg["status"]),
        cursor="pointer",
        _hover={"opacity": "0.85", "filter": "brightness(1.08)"},
        transition="all 0.15s ease",
    )


def assessment_donut_svg() -> rx.Component:
    return rx.el.svg(
        rx.el.g(
            rx.foreach(AdminState.assessment_donut_segments, _donut_segment_slice),
            # Center circular cutout
            rx.el.circle(
                cx="100",
                cy="100",
                r="53",
                fill="#ffffff",
            ),
            rx.el.text(
                AdminState.assessment_donut_total_count.to_string(),
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
            rx.el.text(
                "Assessments",
                x="100",
                y="120",
                text_anchor="middle",
                dominant_baseline="central",
                fill="#64748B",
                font_size="10",
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


def status_overview_card(
    dot_color: str,
    title: str,
    count: rx.Var | str,
    subtitle: rx.Var | str,
    card_bg: str,
    card_border: str,
    on_click: rx.event.EventHandler | None = None,
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
        cursor="pointer",
        _hover={
            "box_shadow": "0 4px 14px rgba(0, 0, 0, 0.08)",
            "transform": "translateY(-1px)",
            "border_color": dot_color,
        },
        transition="all 0.15s ease",
        on_click=on_click,
    )


def _assessment_overview_modal_row(item: dict) -> rx.Component:
    badge_in_progress = rx.hstack(
        rx.box(width="6px", height="6px", border_radius="50%", background="#10B981", flex_shrink="0"),
        rx.text("In Progress", font_family=FONT_BODY, size="1", weight="medium", color="#059669"),
        spacing="2",
        align_items="center",
        background="#ECFDF5",
        border="1px solid #D1FAE5",
        padding="0.25em 0.75em",
        border_radius="999px",
        display="inline-flex",
    )
    badge_not_completed = rx.hstack(
        rx.box(width="6px", height="6px", border_radius="50%", background="#F59E0B", flex_shrink="0"),
        rx.text("Not Completed", font_family=FONT_BODY, size="1", weight="medium", color="#D97706"),
        spacing="2",
        align_items="center",
        background="#FFFBEB",
        border="1px solid #FEF3C7",
        padding="0.25em 0.75em",
        border_radius="999px",
        display="inline-flex",
    )
    badge_completed = rx.hstack(
        rx.box(width="6px", height="6px", border_radius="50%", background="#2563EB", flex_shrink="0"),
        rx.text("Completed", font_family=FONT_BODY, size="1", weight="medium", color="#1D4ED8"),
        spacing="2",
        align_items="center",
        background="#EFF6FF",
        border="1px solid #DBEAFE",
        padding="0.25em 0.75em",
        border_radius="999px",
        display="inline-flex",
    )
    status_badge = rx.match(
        item["status"],
        ("In Progress", badge_in_progress),
        ("Completed", badge_completed),
        badge_not_completed,
    )

    return rx.table.row(
        rx.table.cell(
            rx.text(item["num"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
            width="12%",
            vertical_align="middle",
        ),
        rx.table.cell(
            rx.text(item["name"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
            width="58%",
            vertical_align="middle",
        ),
        rx.table.cell(
            status_badge,
            width="30%",
            vertical_align="middle",
        ),
        style={
            "&:hover": {"background": "#F8FAFC"},
            "transition": "background 0.12s ease",
            "borderBottom": f"1px solid {COLORS['line']}",
        },
    )


def assessment_overview_modal() -> rx.Component:
    icon_in_progress = rx.box(
        rx.icon("file-text", size=22, color="#10B981"),
        background="#ECFDF5",
        border="1px solid #D1FAE5",
        padding="0.65em",
        border_radius="12px",
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )
    icon_not_completed = rx.box(
        rx.icon("file-text", size=22, color="#F59E0B"),
        background="#FFFBEB",
        border="1px solid #FEF3C7",
        padding="0.65em",
        border_radius="12px",
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )
    icon_completed = rx.box(
        rx.icon("file-text", size=22, color="#2563EB"),
        background="#EFF6FF",
        border="1px solid #DBEAFE",
        padding="0.65em",
        border_radius="12px",
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )
    status_icon = rx.match(
        AdminState.assessment_overview_modal_status,
        ("In Progress", icon_in_progress),
        ("Completed", icon_completed),
        icon_not_completed,
    )

    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Modal Header
                rx.hstack(
                    rx.hstack(
                        status_icon,
                        rx.vstack(
                            rx.text(
                                AdminState.assessment_overview_modal_title,
                                font_family=FONT_BODY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                AdminState.assessment_overview_modal_subtitle,
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
                        rx.box(
                            rx.icon("x", size=18, color=COLORS["slate"]),
                            cursor="pointer",
                            padding="0.35em",
                            border_radius="6px",
                            _hover={"background": COLORS["canvas"], "color": COLORS["ink"]},
                            transition="all 0.15s ease",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        )
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                ),

                # Table of assessments
                rx.box(
                    rx.cond(
                        AdminState.assessment_overview_modal_items.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        rx.text("#", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                        width="12%",
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Assessment Name", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                        width="58%",
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Status", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                        width="30%",
                                    ),
                                    style={"background": "#F5F3FF"},
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(AdminState.assessment_overview_modal_items, _assessment_overview_modal_row)
                            ),
                            width="100%",
                        ),
                        rx.box(
                            rx.text(
                                "No assessments found for this status.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            padding="2.5em 1em",
                            text_align="center",
                            width="100%",
                        ),
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    overflow="hidden",
                    width="100%",
                    max_height="360px",
                    overflow_y="auto",
                ),

                # Modal Footer
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color=COLORS["ink"],
                            background=COLORS["surface"],
                            border=f"1px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.5em 1.6em",
                            font_family=FONT_BODY,
                            font_size="13px",
                            font_weight="medium",
                            cursor="pointer",
                            _hover={"background": "#F8FAFC"},
                            transition="all 0.15s ease",
                        )
                    ),
                    width="100%",
                    padding_top="0.8em",
                ),
                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "620px"},
            background=COLORS["surface"],
            border_radius="16px",
            padding="1.6em",
        ),
        open=AdminState.show_assessment_overview_modal,
        on_open_change=AdminState.set_show_assessment_overview_modal,
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
                        on_click=AdminState.open_assessment_overview_modal("In Progress"),
                    ),
                    status_overview_card(
                        dot_color="#F59E0B",
                        title="Not Completed",
                        count=AdminState.dashboard_assessments_not_completed_count.to_string(),
                        subtitle=AdminState.dashboard_assessments_not_completed_subtitle,
                        card_bg="#FFFBEB",
                        card_border="#FEF3C7",
                        on_click=AdminState.open_assessment_overview_modal("Not Completed"),
                    ),
                    status_overview_card(
                        dot_color="#2563EB",
                        title="Completed",
                        count=AdminState.dashboard_assessments_completed_count.to_string(),
                        subtitle=AdminState.dashboard_assessments_completed_subtitle,
                        card_bg="#EFF6FF",
                        card_border="#DBEAFE",
                        on_click=AdminState.open_assessment_overview_modal("Completed"),
                    ),
                    spacing="4",
                    align_items="stretch",
                    flex="1",
                ),
                spacing="4",
                align_items="center",
                width="100%",
                padding_y="0.5em",
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
        # ── 2 KPI Stat Cards (Total Facilitators & Total Candidates) ──
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
            spacing="4",
            width="100%",
        ),

        # ── Assessment Overview (expanded) ───────────────────────────
        assessments_overview_card(),

        # ── Recent Assessments Table ──────────────────────────────────
        recent_assessments_card(),

        # ── Assessment Overview Modal ─────────────────────────────────
        assessment_overview_modal(),

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
