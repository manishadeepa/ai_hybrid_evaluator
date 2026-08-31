"""Admin Reports page — assessment-level breakdown + submitted facilitator reports."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminState, AdminReportsState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────
# Summary stat card (top row)
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
# Approval / Assessment status badges
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


def report_status_badge() -> rx.Component:
    """Green 'Submitted' badge for submitted reports."""
    return rx.hstack(
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#059669",
            flex_shrink="0",
        ),
        rx.text("Submitted", font_family=FONT_BODY, size="1",
                weight="bold", color="#059669"),
        spacing="1",
        align_items="center",
        background="#ECFDF3",
        border="1px solid #A6F4C5",
        padding="0.25em 0.75em",
        border_radius="999px",
    )


# ─────────────────────────────────────────────────────────────
# Assessment breakdown row (existing)
# ─────────────────────────────────────────────────────────────

def report_row(a: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(a["name"], font_family=FONT_BODY, size="2",
                    weight="bold", color=COLORS["ink"]),
        ),
        rx.table.cell(
            rx.text(a["facilitator_name"], font_family=FONT_BODY,
                    size="2", color=COLORS["slate"]),
        ),
        rx.table.cell(
            rx.text(
                a["assigned_candidates"].length().to_string(), " candidates",
                font_family=FONT_BODY, size="2", color=COLORS["slate"],
            ),
        ),
        rx.table.cell(
            rx.text(
                a["tests"].length().to_string(), " + Final",
                font_family=FONT_BODY, size="2", color=COLORS["slate"],
            ),
        ),
        rx.table.cell(assessment_status_badge(a["status"])),
        rx.table.cell(approval_badge(a.get("approval_status", "pending"))),
    )


# ─────────────────────────────────────────────────────────────
# Submitted Report list row
# ─────────────────────────────────────────────────────────────

def submitted_report_row(r: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(r["assessment_name"], font_family=FONT_BODY, size="2",
                        weight="bold", color=COLORS["ink"]),
                rx.hstack(
                    rx.text("Report ID:", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(r["report_id"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="1",
                ),
                spacing="0",
                align_items="start",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon("user", size=14, color=COLORS["slate"]),
                rx.text(r["facilitator_name"], font_family=FONT_BODY,
                        size="2", color=COLORS["slate"]),
                spacing="1",
                align_items="center",
            ),
        ),
        rx.table.cell(
            rx.text(
                r["candidate_count"].to_string(),
                " candidates",
                font_family=FONT_BODY, size="2", color=COLORS["slate"],
            ),
        ),
        rx.table.cell(
            rx.text(
                r["overall_score"].to_string(), "%",
                font_family=FONT_BODY, size="2", weight="bold",
                color="#4F46E5",
            ),
        ),
        rx.table.cell(
            rx.text(r["submitted_date"], font_family=FONT_BODY,
                    size="2", color=COLORS["slate"]),
        ),
        rx.table.cell(report_status_badge()),
        rx.table.cell(
            rx.button(
                rx.icon("eye", size=14),
                "View Report",
                on_click=AdminReportsState.open_report(r["report_id"], False),
                size="2",
                variant="soft",
                color_scheme="indigo",
                font_family=FONT_BODY,
                cursor="pointer",
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────
# Report Detail — Horizontal bar chart row
# ─────────────────────────────────────────────────────────────

def report_detail_bar_row(item: dict) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(item["name"], font_family=FONT_BODY, size="2",
                    weight="bold", color=COLORS["ink"]),
            rx.spacer(),
            rx.text(
                item["score"].to_string(), "%",
                font_family=FONT_BODY, size="2", weight="bold",
                color=rx.cond(item["score"].to(int) >= 80, "#059669", "#4F46E5"),
            ),
            spacing="2",
            width="100%",
        ),
        rx.box(
            # Filled bar
            rx.box(
                width=f"{item['score']}%",
                height="100%",
                background=rx.cond(
                    item["score"].to(int) >= 80,
                    "linear-gradient(90deg, #6366F1, #059669)",
                    "linear-gradient(90deg, #818CF8, #4F46E5)",
                ),
                border_radius="6px",
                transition="width 0.3s ease",
            ),
            # 50% threshold line
            rx.box(
                position="absolute",
                left="50%",
                top="0",
                bottom="0",
                width="2px",
                border_left="2px dashed #EF4444",
                z_index="2",
            ),
            height="14px",
            background="#F1F5F9",
            border="1px solid #E2E8F0",
            border_radius="6px",
            overflow="hidden",
            position="relative",
            width="100%",
        ),
        spacing="1",
        width="100%",
        padding_y="0.3em",
    )


# ─────────────────────────────────────────────────────────────
# Report Detail — Vertical bar (for Overall Test scores)
# ─────────────────────────────────────────────────────────────

def report_detail_vertical_bar(item: dict) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.cond(
                item["is_final"],
                rx.vstack(
                    rx.box(
                        rx.icon("award", size=13, color="#D97706"),
                        background="#FEF3C7",
                        padding="2px",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text(
                        item["score"].to_string(), "%",
                        font_family=FONT_BODY, size="2", weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="0",
                    align_items="center",
                    position="absolute",
                    bottom=f"calc({item['score']}% + 4px)",
                    left="50%",
                    transform="translateX(-50%)",
                    width="100%",
                ),
                rx.text(
                    item["score"].to_string(), "%",
                    font_family=FONT_BODY, size="2", weight="bold",
                    color=COLORS["ink"],
                    position="absolute",
                    bottom=f"calc({item['score']}% + 6px)",
                    left="50%",
                    transform="translateX(-50%)",
                    width="100%",
                    text_align="center",
                ),
            ),
            # The bar
            rx.box(
                position="absolute",
                bottom="0",
                left="50%",
                transform="translateX(-50%)",
                width="54px",
                height=f"{item['score']}%",
                background=rx.cond(item["is_final"], "#4F46E5", "#818CF8"),
                border_radius="6px 6px 0 0",
                transition="height 0.3s ease",
            ),
            position="relative",
            width="76px",
            height="180px",
        ),
        rx.text(
            item["name"],
            font_family=FONT_BODY, size="2", weight="medium",
            color=COLORS["slate"], text_align="center",
            padding_top="0.4em",
        ),
        spacing="0",
        align_items="center",
    )


# ─────────────────────────────────────────────────────────────
# Report Detail — Dimension tab pill
# ─────────────────────────────────────────────────────────────

def report_dim_pill(tab_key: str, label: str) -> rx.Component:
    is_active = AdminReportsState.report_detail_tab == tab_key
    return rx.box(
        rx.text(
            label,
            font_family=FONT_BODY, size="2",
            weight=rx.cond(is_active, "bold", "medium"),
            color=rx.cond(is_active, "white", "#475467"),
        ),
        background=rx.cond(is_active, "#4F46E5", "#F1F5F9"),
        padding="0.4em 1em",
        border_radius="8px",
        cursor="pointer",
        on_click=AdminReportsState.set_report_detail_tab(tab_key),
        _hover={"background": rx.cond(is_active, "#4338CA", "#E2E8F0")},
        transition="all 0.15s ease",
    )


# ─────────────────────────────────────────────────────────────
# Report Detail — Candidate row
# ─────────────────────────────────────────────────────────────

def report_cand_row(cand: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.badge(
                "#", cand["rank"].to_string(),
                color_scheme="indigo", variant="solid", size="1",
            ),
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(cand["name"], font_family=FONT_BODY, size="2",
                        weight="bold", color=COLORS["ink"]),
                rx.text(cand["emp_id"], font_family=FONT_BODY, size="1",
                        color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(
                    cand["overall_score"].to_string(), "%",
                    font_family=FONT_BODY, size="2", weight="bold",
                    color=COLORS["ink"], min_width="38px",
                ),
                rx.box(
                    rx.box(
                        width=f"{cand['overall_score']}%",
                        height="100%",
                        background="#4F46E5",
                        border_radius="4px",
                    ),
                    width="88px",
                    height="8px",
                    background="#EEF2FF",
                    border_radius="4px",
                    overflow="hidden",
                ),
                spacing="2",
                align_items="center",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(
                    cand["final_test_score"].to_string(), "%",
                    font_family=FONT_BODY, size="2", weight="bold",
                    color=COLORS["ink"], min_width="38px",
                ),
                rx.box(
                    rx.box(
                        width=f"{cand['final_test_score']}%",
                        height="100%",
                        background="#059669",
                        border_radius="4px",
                    ),
                    width="88px",
                    height="8px",
                    background="#ECFDF3",
                    border_radius="4px",
                    overflow="hidden",
                ),
                spacing="2",
                align_items="center",
            ),
        ),
        rx.table.cell(
            rx.badge(cand["result"], color_scheme="green", variant="soft", size="1"),
        ),
    )


# ─────────────────────────────────────────────────────────────
# Report Detail Modal — full view
# ─────────────────────────────────────────────────────────────

def report_detail_modal() -> rx.Component:
    r = AdminReportsState.current_report
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # ── Modal Header ────────────────────────────────────────
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-bar-chart", size=20, color="white"),
                            background="linear-gradient(135deg, #4F46E5, #7C3AED)",
                            padding="0.55em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.text(
                                    "Assessment Report",
                                    font_family=FONT_DISPLAY, size="4",
                                    weight="bold", color=COLORS["ink"],
                                ),
                                report_status_badge(),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.text(
                                "Report submitted by the Facilitator",
                                font_family=FONT_BODY, size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.button(
                            rx.icon(
                                rx.cond(AdminReportsState.is_full_view, "minimize-2", "maximize-2"),
                                size=14,
                            ),
                            rx.cond(AdminReportsState.is_full_view, "Exit Full View", "Full View"),
                            on_click=AdminReportsState.toggle_full_view,
                            size="2",
                            variant="outline",
                            color_scheme="indigo",
                            font_family=FONT_BODY,
                            cursor="pointer",
                        ),
                        rx.button(
                            rx.icon("download", size=14),
                            "Export PDF",
                            on_click=AdminReportsState.mock_export_report,
                            size="2",
                            variant="outline",
                            color=COLORS["primary"],
                            border=f"1px solid {COLORS['primary']}",
                            font_family=FONT_BODY,
                            cursor="pointer",
                        ),
                        rx.dialog.close(
                            rx.button(
                                rx.icon("x", size=14),
                                variant="ghost",
                                size="2",
                                color_scheme="gray",
                                font_family=FONT_BODY,
                                cursor="pointer",
                            ),
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="1.2em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # ── 1. Assessment Information ───────────────────────────
                rx.box(
                    rx.hstack(
                        rx.icon("clipboard-list", size=16, color="#4F46E5"),
                        rx.text("Assessment Information", font_family=FONT_BODY,
                                size="3", weight="bold", color=COLORS["ink"]),
                        spacing="2",
                        align_items="center",
                        padding_bottom="0.8em",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Assessment", font_family=FONT_BODY, size="1",
                                    weight="bold", color=COLORS["slate"]),
                            rx.text(r["assessment_name"], font_family=FONT_BODY,
                                    size="3", weight="bold", color=COLORS["ink"]),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.box(width="1px", height="40px", background=COLORS["line"]),
                        rx.vstack(
                            rx.text("Facilitator", font_family=FONT_BODY, size="1",
                                    weight="bold", color=COLORS["slate"]),
                            rx.hstack(
                                rx.icon("user", size=14, color="#4F46E5"),
                                rx.text(r["facilitator_name"], font_family=FONT_BODY,
                                        size="3", weight="bold", color=COLORS["ink"]),
                                spacing="1",
                                align_items="center",
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.box(width="1px", height="40px", background=COLORS["line"]),
                        rx.vstack(
                            rx.text("Assessment Date", font_family=FONT_BODY, size="1",
                                    weight="bold", color=COLORS["slate"]),
                            rx.text(r["assessment_date"], font_family=FONT_BODY,
                                    size="3", weight="bold", color=COLORS["ink"]),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.box(width="1px", height="40px", background=COLORS["line"]),
                        rx.vstack(
                            rx.text("Submitted Date", font_family=FONT_BODY, size="1",
                                    weight="bold", color=COLORS["slate"]),
                            rx.text(r["submitted_date"], font_family=FONT_BODY,
                                    size="3", weight="bold", color=COLORS["ink"]),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="5",
                        align_items="center",
                        width="100%",
                    ),
                    background="#F8FAFF",
                    border=f"1px solid {COLORS['line']}",
                    border_radius="12px",
                    padding="1.2em 1.4em",
                ),

                # ── 2. Performance Summary Cards ────────────────────────
                rx.hstack(
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("trending-up", size=20, color="#4F46E5"),
                                background="#EEF2FF",
                                padding="0.6em",
                                border_radius="8px",
                            ),
                            rx.vstack(
                                rx.text("OVERALL SCORE", font_family=FONT_BODY,
                                        size="1", weight="bold", color=COLORS["slate"],
                                        letter_spacing="0.04em"),
                                rx.text(
                                    r["overall_score"].to_string(), "%",
                                    font_family=FONT_DISPLAY, size="7",
                                    weight="bold", color="#4F46E5",
                                ),
                                rx.text("All Assessments", font_family=FONT_BODY,
                                        size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="3",
                            align_items="center",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="12px",
                        padding="1em 1.2em",
                        flex="1",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("star", size=20, color="#059669"),
                                background="#ECFDF3",
                                padding="0.6em",
                                border_radius="8px",
                            ),
                            rx.vstack(
                                rx.text("FINAL TEST SCORE", font_family=FONT_BODY,
                                        size="1", weight="bold", color=COLORS["slate"],
                                        letter_spacing="0.04em"),
                                rx.text(
                                    r["final_test_score"].to_string(), "%",
                                    font_family=FONT_DISPLAY, size="7",
                                    weight="bold", color="#059669",
                                ),
                                rx.text("Final Assessment", font_family=FONT_BODY,
                                        size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="3",
                            align_items="center",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="12px",
                        padding="1em 1.2em",
                        flex="1",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("shield-check", size=20, color="#2563EB"),
                                background="#EFF6FF",
                                padding="0.6em",
                                border_radius="8px",
                            ),
                            rx.vstack(
                                rx.text("PASSING RATE", font_family=FONT_BODY,
                                        size="1", weight="bold", color=COLORS["slate"],
                                        letter_spacing="0.04em"),
                                rx.text(
                                    r["passing_rate"],
                                    font_family=FONT_DISPLAY, size="7",
                                    weight="bold", color="#2563EB",
                                ),
                                rx.text(r["passing_count"], font_family=FONT_BODY,
                                        size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="3",
                            align_items="center",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="12px",
                        padding="1em 1.2em",
                        flex="1",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.icon("users", size=20, color="#D97706"),
                                background="#FEF3C7",
                                padding="0.6em",
                                border_radius="8px",
                            ),
                            rx.vstack(
                                rx.text("TOTAL CANDIDATES", font_family=FONT_BODY,
                                        size="1", weight="bold", color=COLORS["slate"],
                                        letter_spacing="0.04em"),
                                rx.text(
                                    r["candidate_count"].to_string(),
                                    font_family=FONT_DISPLAY, size="7",
                                    weight="bold", color="#D97706",
                                ),
                                rx.text("Evaluated", font_family=FONT_BODY,
                                        size="1", color=COLORS["slate"]),
                                spacing="0",
                                align_items="start",
                            ),
                            spacing="3",
                            align_items="center",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="12px",
                        padding="1em 1.2em",
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                    flex_wrap="wrap",
                ),

                # ── 3. Key Insight Banner ───────────────────────────────
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("trending-up", size=16, color="#059669"),
                            background="#ECFDF3",
                            padding="0.4em",
                            border_radius="6px",
                        ),
                        rx.text(
                            "Key Insight: ",
                            rx.text.strong("Performance improved by "),
                            rx.text(
                                r["insight_diff"].to_string(),
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color="#059669",
                                display="inline",
                            ),
                            rx.text.strong(" percentage points"),
                            " — from ",
                            r["insight_start"],
                            " to ",
                            r["insight_end"],
                            ".",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["ink"],
                        ),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    background="#ECFDF3",
                    border="1px solid #A6F4C5",
                    border_radius="10px",
                    padding="0.9em 1.2em",
                    width="100%",
                ),

                # ── 4. Analytics — Tabs + Chart ─────────────────────────
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.hstack(
                                rx.icon("bar-chart-2", size=18, color=COLORS["primary"]),
                                rx.text("Performance Analytics", font_family=FONT_BODY,
                                        size="3", weight="bold", color=COLORS["ink"]),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.spacer(),
                            rx.text(
                                "All scores in %  •  Pass Mark: 50%",
                                font_family=FONT_BODY, size="1",
                                color=COLORS["slate"],
                            ),
                            width="100%",
                            align_items="center",
                            padding_bottom="0.8em",
                        ),

                        # Tabs
                        rx.hstack(
                            report_dim_pill("overall", "Overall"),
                            report_dim_pill("co", "CO"),
                            report_dim_pill("lo", "LO"),
                            report_dim_pill("knowledge_type", "Knowledge Type"),
                            report_dim_pill("domain", "Domain"),
                            report_dim_pill("rbt_level", "RBT Level"),
                            spacing="2",
                            width="100%",
                            flex_wrap="wrap",
                            margin_bottom="1.5em",
                        ),

                        # Chart area
                        rx.cond(
                            AdminReportsState.report_detail_tab == "overall",
                            # Vertical bar chart for Overall
                            rx.vstack(
                                rx.hstack(
                                    # Y-axis ticks
                                    rx.vstack(
                                        rx.text("100%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                        rx.text("75%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                        rx.text("50%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                        rx.text("25%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                        rx.text("0%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                        height="180px",
                                        align_items="end",
                                        padding_right="0.5em",
                                        display="flex",
                                        flex_direction="column",
                                        justify_content="space-between",
                                    ),
                                    # Canvas
                                    rx.box(
                                        rx.box(position="absolute", left="0", right="0", top="0%",
                                               border_top="1px dashed #E2E8F0", z_index="1"),
                                        rx.box(position="absolute", left="0", right="0", top="25%",
                                               border_top="1px dashed #E2E8F0", z_index="1"),
                                        rx.box(position="absolute", left="0", right="0", top="50%",
                                               border_top="1.5px dashed #EF4444", z_index="2"),
                                        rx.box(
                                            rx.text("Pass Mark 50%", font_family=FONT_BODY,
                                                    size="1", weight="bold", color="#DC2626"),
                                            background="#FEF2F2",
                                            border="1px solid #FECACA",
                                            border_radius="4px",
                                            padding="0.1em 0.4em",
                                            position="absolute",
                                            right="-90px",
                                            top="calc(50% - 10px)",
                                            z_index="3",
                                        ),
                                        rx.box(position="absolute", left="0", right="0", top="75%",
                                               border_top="1px dashed #E2E8F0", z_index="1"),
                                        rx.box(position="absolute", left="0", right="0", top="100%",
                                               border_top="1px solid #CBD5E1", z_index="1"),
                                        rx.hstack(
                                            rx.foreach(
                                                AdminReportsState.report_test_scores,
                                                lambda item: report_detail_vertical_bar(item),
                                            ),
                                            display="flex",
                                            justify_content="space-around",
                                            align_items="end",
                                            height="180px",
                                            width="100%",
                                            z_index="4",
                                            position="relative",
                                        ),
                                        position="relative",
                                        height="180px",
                                        flex="1",
                                        border_left="1px solid #CBD5E1",
                                        margin_right="100px",
                                    ),
                                    spacing="1",
                                    align_items="center",
                                    width="100%",
                                ),
                                rx.text(
                                    "Assessment / Test",
                                    font_family=FONT_BODY, size="1", weight="bold",
                                    color=COLORS["slate"], text_align="center",
                                    width="100%", padding_top="0.6em",
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            # Horizontal bar chart for CO/LO/etc.
                            rx.vstack(
                                rx.hstack(
                                    rx.text("Dimension / Competency", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                    rx.spacer(),
                                    rx.text("— 50% Pass Mark", font_family=FONT_BODY,
                                            size="1", weight="bold", color="#DC2626"),
                                    rx.text("Score (%)", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                    width="100%",
                                    padding_bottom="0.4em",
                                    border_bottom="1px solid #F1F5F9",
                                ),
                                rx.vstack(
                                    rx.foreach(
                                        AdminReportsState.report_active_dimension_items,
                                        lambda item: report_detail_bar_row(item),
                                    ),
                                    spacing="2",
                                    width="100%",
                                    padding_top="0.4em",
                                ),
                                spacing="1",
                                width="100%",
                            ),
                        ),

                        spacing="0",
                        width="100%",
                        align_items="stretch",
                    ),
                    background=COLORS["surface"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="12px",
                    padding="1.4em",
                    width="100%",
                ),

                # ── 5. Candidate Performance Table ──────────────────────
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("users", size=18, color=COLORS["primary"]),
                            rx.text("Candidate Performance", font_family=FONT_BODY,
                                    size="3", weight="bold", color=COLORS["ink"]),
                            spacing="2",
                            align_items="center",
                            padding_bottom="0.8em",
                        ),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        rx.text("Rank", font_family=FONT_BODY,
                                                size="1", weight="bold", color=COLORS["slate"]),
                                        width="60px",
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Candidate", font_family=FONT_BODY,
                                                size="1", weight="bold", color=COLORS["slate"]),
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Overall Score", font_family=FONT_BODY,
                                                size="1", weight="bold", color=COLORS["slate"]),
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Final Test Score", font_family=FONT_BODY,
                                                size="1", weight="bold", color=COLORS["slate"]),
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Result", font_family=FONT_BODY,
                                                size="1", weight="bold", color=COLORS["slate"]),
                                        width="90px",
                                    ),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    AdminReportsState.report_candidates,
                                    lambda cand: report_cand_row(cand),
                                ),
                            ),
                            width="100%",
                        ),
                        spacing="0",
                        width="100%",
                        align_items="stretch",
                    ),
                    background=COLORS["surface"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="12px",
                    padding="1.4em",
                    width="100%",
                ),

                spacing="4",
                width="100%",
                align_items="stretch",
            ),
            style={
                "maxWidth": rx.cond(AdminReportsState.is_full_view, "100vw", "960px"),
                "width": rx.cond(AdminReportsState.is_full_view, "100vw", "95vw"),
                "maxHeight": rx.cond(AdminReportsState.is_full_view, "100vh", "90vh"),
                "height": rx.cond(AdminReportsState.is_full_view, "100vh", "auto"),
                "borderRadius": rx.cond(AdminReportsState.is_full_view, "0px", "16px"),
                "padding": rx.cond(AdminReportsState.is_full_view, "2em 3em", "1.5em"),
                "overflowY": "auto",
            },
        ),
        open=AdminReportsState.show_report_detail,
        on_open_change=AdminReportsState.set_show_report_detail,
    )


# ─────────────────────────────────────────────────────────────
# Reports page
# ─────────────────────────────────────────────────────────────

def reports_page() -> rx.Component:
    content = rx.vstack(

        # ── 1. Summary cards (existing) ────────────────────────────────
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

        # ── 2. Submitted Reports from Facilitators (NEW) ───────────────
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("inbox", size=16, color="#059669"),
                            background="#ECFDF3",
                            padding="0.45em",
                            border_radius="8px",
                        ),
                        rx.vstack(
                            rx.text("Submitted Reports", font_family=FONT_BODY,
                                    size="3", weight="bold", color=COLORS["ink"]),
                            rx.text(
                                "Reports submitted by Facilitators from the Results page",
                                font_family=FONT_BODY, size="1", color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.badge(
                        AdminReportsState.submitted_reports.length().to_string(), " submitted",
                        color_scheme="green",
                        variant="soft",
                        size="2",
                        font_family=FONT_BODY,
                    ),
                    width="100%",
                    align_items="center",
                    padding="1em 1.2em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),
                rx.cond(
                    AdminReportsState.submitted_reports.length() == 0,
                    rx.box(
                        rx.vstack(
                            rx.icon("inbox", size=28, color=COLORS["slate"]),
                            rx.text(
                                "No reports submitted yet. Facilitators submit reports from the Results tab.",
                                font_family=FONT_BODY, size="2",
                                color=COLORS["slate"], text_align="center",
                            ),
                            align_items="center",
                            spacing="2",
                        ),
                        padding="3em",
                        display="flex",
                        justify_content="center",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("Assessment", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Facilitator", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Candidates", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Avg. Score", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Submitted", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Status", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Action", font_family=FONT_BODY,
                                            size="1", weight="bold", color=COLORS["slate"]),
                                ),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminReportsState.submitted_reports,
                                lambda r: submitted_report_row(r),
                            ),
                        ),
                        width="100%",
                    ),
                ),
                spacing="0",
                width="100%",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            overflow="hidden",
            width="100%",
        ),

        # ── 3. Assessment Breakdown (existing) ─────────────────────────
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
                    AdminState.total_assessments.to_string(), " total records",
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

        # Report Detail Modal
        report_detail_modal(),

        spacing="5",
        width="100%",
        align_items="stretch",
    )

    return admin_shell(
        active="reports",
        title="Reports",
        subtitle="Assessment performance overview and organization-wide analytics.",
        content=content,
    )