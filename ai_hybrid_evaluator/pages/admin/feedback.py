"""Admin Feedback Management page."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminFeedbackState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY

_LINE = COLORS["line"]
_PRIMARY = COLORS["primary"]
_SLATE = COLORS["slate"]
_INK = COLORS["ink"]
_SURFACE = COLORS["surface"]
_CANVAS = COLORS["canvas"]
_P_SOFT = COLORS["primary_soft"]
_PLACEHOLDER = COLORS["placeholder"]


def _star(filled: rx.Var) -> rx.Component:
    return rx.icon(
        "star", size=13,
        color=rx.cond(filled, "#F59E0B", "#D1D5DB"),
        fill=rx.cond(filled, "#F59E0B", "transparent"),
    )



def render_stars(row: dict, rating_str_key: str = "rating_str") -> rx.Component:
    """Render 5 stars using pre-computed boolean fields star1-star5 from the row dict."""
    return rx.hstack(
        _star(row["star1"]),
        _star(row["star2"]),
        _star(row["star3"]),
        _star(row["star4"]),
        _star(row["star5"]),
        rx.text(row[rating_str_key], font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
        spacing="1", align_items="center",
    )


def candidate_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["id"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(
            rx.vstack(
                rx.text(row["candidate_name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                rx.text(row["candidate_id"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0", align_items="start",
            ),
        ),
        rx.table.cell(rx.text(row["assessment"], font_family=FONT_BODY, size="2", color=COLORS["ink"])),
        rx.table.cell(rx.text(row["test"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(
            rx.text(
                row["preview"], font_family=FONT_BODY, size="2", color=COLORS["slate"],
                style={"fontStyle": "italic", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "maxWidth": "240px"},
            ),
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(row["date_line"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                rx.cond(row["time_line"] != "", rx.text(row["time_line"], font_family=FONT_BODY, size="1", color=COLORS["slate"])),
                spacing="0", align_items="start",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(rx.icon("eye", size=14), size="1", variant="ghost", cursor="pointer",
                               on_click=AdminFeedbackState.select_entry(row),
                               _hover={"background": COLORS["primary_soft"]}),
                rx.icon_button(rx.icon("ellipsis-vertical", size=14, color=COLORS["slate"]), size="1", variant="ghost"),
                spacing="1", align_items="center",
            ),
        ),
        _hover={"background": "#F8FAFC"}, cursor="pointer",
        on_click=AdminFeedbackState.select_entry(row),
    )


def facilitator_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["id"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
        rx.table.cell(rx.text(row["assessment"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"])),
        rx.table.cell(
            rx.badge(rx.icon("user", size=11), row["facilitator"], variant="soft", color_scheme="indigo", size="1"),
        ),
        rx.table.cell(
            rx.text(
                row["preview"], font_family=FONT_BODY, size="2", color=COLORS["slate"],
                style={"fontStyle": "italic", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "maxWidth": "320px"},
            ),
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(row["date_line"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                rx.cond(row["time_line"] != "", rx.text(row["time_line"], font_family=FONT_BODY, size="1", color=COLORS["slate"])),
                spacing="0", align_items="start",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(rx.icon("eye", size=14), size="1", variant="ghost", cursor="pointer",
                               on_click=AdminFeedbackState.select_entry(row),
                               _hover={"background": COLORS["primary_soft"]}),
                rx.icon_button(rx.icon("ellipsis-vertical", size=14, color=COLORS["slate"]), size="1", variant="ghost"),
                spacing="1", align_items="center",
            ),
        ),
        _hover={"background": "#F8FAFC"}, cursor="pointer",
        on_click=AdminFeedbackState.select_entry(row),
    )


def _qa_card(item: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                item["question"],
                font_family=FONT_BODY,
                size="1",
                weight="bold",
                color=COLORS["slate"],
            ),
            rx.text(
                item["answer"],
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                style={"lineHeight": "1.5"},
            ),
            spacing="1",
            align_items="start",
            width="100%",
        ),
        background="#F8FAFC",
        border=f"1px solid {_LINE}",
        border_radius="8px",
        padding="0.85em 1em",
        width="100%",
    )


def feedback_details_panel() -> rx.Component:
    e = AdminFeedbackState.selected_entry
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Feedback Details", size="3", font_family=FONT_DISPLAY, color=COLORS["ink"], weight="bold"),
                rx.spacer(),
                rx.icon_button(rx.icon("x", size=16), variant="ghost", size="1", cursor="pointer",
                               on_click=AdminFeedbackState.close_details_panel),
                width="100%", align_items="center",
                padding="1em 1.2em 0.8em 1.2em",
                border_bottom=f"1px solid {_LINE}",
            ),
            rx.cond(
                e["type"] == "candidate",
                rx.hstack(
                    rx.center(
                        rx.text(e["initial"], font_family=FONT_DISPLAY, weight="bold", size="4", color=COLORS["primary"]),
                        background=COLORS["primary_soft"], width="44px", height="44px", border_radius="999px",
                    ),
                    rx.vstack(
                        rx.text(e["candidate_name"], font_family=FONT_BODY, weight="bold", size="3", color=COLORS["ink"]),
                        rx.text(e["candidate_id"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        spacing="0", align_items="start",
                    ),
                    spacing="3", align_items="center",
                    padding="1em 1.2em", width="100%",
                ),
                rx.hstack(
                    rx.center(
                        rx.icon("user", size=22, color=COLORS["primary"]),
                        background=COLORS["primary_soft"], width="44px", height="44px", border_radius="999px",
                    ),
                    rx.vstack(
                        rx.text(e["facilitator"], font_family=FONT_BODY, weight="bold", size="3", color=COLORS["ink"]),
                        rx.badge("Facilitator", variant="soft", color_scheme="indigo", size="1"),
                        spacing="1", align_items="start",
                    ),
                    spacing="3", align_items="center",
                    padding="1em 1.2em", width="100%",
                ),
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Assessment", font_family=FONT_BODY, size="2", color=COLORS["slate"], min_width="100px"),
                    rx.text(e["assessment"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                    width="100%",
                ),
                rx.cond(
                    e["type"] == "candidate",
                    rx.hstack(
                        rx.text("Test", font_family=FONT_BODY, size="2", color=COLORS["slate"], min_width="100px"),
                        rx.text(e["test"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        width="100%",
                    ),
                    rx.hstack(
                        rx.text("Facilitator", font_family=FONT_BODY, size="2", color=COLORS["slate"], min_width="100px"),
                        rx.text(e["facilitator"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        width="100%",
                    ),
                ),
                rx.hstack(
                    rx.text("Submitted On", font_family=FONT_BODY, size="2", color=COLORS["slate"], min_width="100px"),
                    rx.text(e["submitted_on"], font_family=FONT_BODY, size="2", color=COLORS["ink"]),
                    width="100%",
                ),
                spacing="2", padding="0 1.2em 1em 1.2em", width="100%",
            ),
            rx.vstack(
                rx.text("Form Responses", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                rx.cond(
                    AdminFeedbackState.selected_qa_pairs.length() > 0,
                    rx.vstack(
                        rx.foreach(AdminFeedbackState.selected_qa_pairs, _qa_card),
                        spacing="2",
                        width="100%",
                        align_items="stretch",
                    ),
                    rx.box(
                        rx.text(
                            "No responses recorded.",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                            style={"fontStyle": "italic"},
                        ),
                        background="#F8FAFC",
                        border=f"1px solid {_LINE}",
                        border_radius="8px",
                        padding="0.9em 1.1em",
                        width="100%",
                    ),
                ),
                spacing="2", padding="0 1.2em 1.2em 1.2em",
                width="100%", align_items="start",
            ),
            spacing="0", width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {_LINE}",
        border_radius="10px",
        width="370px", min_width="340px",
        overflow="hidden", align_self="start",
    )


def feedback_table_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("message-square", size=16, color=COLORS["primary"]),
                rx.text(
                    rx.cond(
                        AdminFeedbackState.active_tab == "candidate",
                        "Candidate Feedback (",
                        "Facilitator Feedback (",
                    ) + AdminFeedbackState.current_tab_count.to_string() + ")",
                    font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"],
                ),
                spacing="2", align_items="center",
                padding="1em 1.2em 0.8em 1.2em",
                border_bottom=f"1px solid {_LINE}",
                width="100%",
            ),
            rx.cond(
                AdminFeedbackState.paginated_entries.length() == 0,
                rx.center(
                    rx.vstack(
                        rx.icon("message-square-off", size=32, color=COLORS["slate"]),
                        rx.text("No feedback records found", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                        rx.text("Try adjusting your filters.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                        spacing="2", align_items="center", padding="4em 1em",
                    ), width="100%",
                ),
                rx.cond(
                    AdminFeedbackState.active_tab == "candidate",
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("#", width="4%"),
                                rx.table.column_header_cell("Candidate Name", width="20%"),
                                rx.table.column_header_cell("Assessment", width="15%"),
                                rx.table.column_header_cell("Test", width="12%"),
                                rx.table.column_header_cell("Feedback (Preview)", width="28%"),
                                rx.table.column_header_cell("Submitted On", width="14%"),
                                rx.table.column_header_cell("Actions", width="7%"),
                            ),
                        ),
                        rx.table.body(rx.foreach(AdminFeedbackState.paginated_entries, candidate_row)),
                        width="100%",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("#", width="5%"),
                                rx.table.column_header_cell("Assessment", width="22%"),
                                rx.table.column_header_cell("Facilitator", width="18%"),
                                rx.table.column_header_cell("Feedback (Preview)", width="33%"),
                                rx.table.column_header_cell("Submitted On", width="14%"),
                                rx.table.column_header_cell("Actions", width="8%"),
                            ),
                        ),
                        rx.table.body(rx.foreach(AdminFeedbackState.paginated_entries, facilitator_row)),
                        width="100%",
                    ),
                ),
            ),
            rx.hstack(
                rx.text(AdminFeedbackState.pagination_info_str, font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                rx.spacer(),
                rx.hstack(
                    rx.icon_button(rx.icon("chevron-left", size=15), variant="outline", size="1", cursor="pointer",
                                   disabled=AdminFeedbackState.current_page <= 1,
                                   on_click=AdminFeedbackState.prev_page),
                    rx.badge(AdminFeedbackState.current_page.to_string(),
                             background=COLORS["primary"], color="white",
                             size="2", border_radius="6px", padding="0.2em 0.7em"),
                    rx.icon_button(rx.icon("chevron-right", size=15), variant="outline", size="1", cursor="pointer",
                                   disabled=AdminFeedbackState.current_page >= AdminFeedbackState.total_pages,
                                   on_click=AdminFeedbackState.next_page),
                    spacing="2", align_items="center",
                ),
                padding="0.8em 1.2em",
                border_top=f"1px solid {_LINE}",
                width="100%", align_items="center",
            ),
            spacing="0", width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {_LINE}",
        border_radius="10px",
        width="100%", overflow="hidden", flex="1",
    )


def admin_feedback_page() -> rx.Component:
    content = rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.heading("Feedback Management", size="6", font_family=FONT_DISPLAY, color=COLORS["ink"], weight="bold"),
                rx.text(
                    "View and manage feedback from candidates and facilitators across all assessments.",
                    size="2", color=COLORS["slate"], font_family=FONT_BODY,
                ),
                spacing="1", align_items="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=16), "Export Feedback",
                variant="outline", color=COLORS["primary"],
                border=f"1px solid {_PRIMARY}",
                background=COLORS["surface"], font_family=FONT_BODY,
                border_radius="8px",
                _hover={"background": COLORS["primary_soft"]},
                on_click=AdminFeedbackState.export_feedback,
            ),
            width="100%", align_items="center",
        ),
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.hstack(
                        rx.icon("message-square-heart", size=16),
                        rx.text(
                            "Candidate Feedback (" + AdminFeedbackState.total_candidate_count.to_string() + ")",
                            font_family=FONT_BODY, font_weight="600", size="2",
                        ),
                        spacing="2", align_items="center",
                    ),
                    background=rx.cond(AdminFeedbackState.active_tab == "candidate", "#EDE9FE", "transparent"),
                    color=rx.cond(AdminFeedbackState.active_tab == "candidate", COLORS["primary"], COLORS["slate"]),
                    border_bottom=rx.cond(AdminFeedbackState.active_tab == "candidate", f"2.5px solid {_PRIMARY}", "2.5px solid transparent"),
                    border_radius="8px 8px 0 0",
                    padding="0.65em 1.5em", cursor="pointer",
                    _hover={"color": COLORS["primary"]},
                    on_click=AdminFeedbackState.set_active_tab("candidate"),
                ),
                rx.box(
                    rx.hstack(
                        rx.icon("users", size=16),
                        rx.text(
                            "Facilitator Feedback (" + AdminFeedbackState.total_facilitator_count.to_string() + ")",
                            font_family=FONT_BODY, font_weight="600", size="2",
                        ),
                        spacing="2", align_items="center",
                    ),
                    background=rx.cond(AdminFeedbackState.active_tab == "facilitator", "#EDE9FE", "transparent"),
                    color=rx.cond(AdminFeedbackState.active_tab == "facilitator", COLORS["primary"], COLORS["slate"]),
                    border_bottom=rx.cond(AdminFeedbackState.active_tab == "facilitator", f"2.5px solid {_PRIMARY}", "2.5px solid transparent"),
                    border_radius="8px 8px 0 0",
                    padding="0.65em 1.5em", cursor="pointer",
                    _hover={"color": COLORS["primary"]},
                    on_click=AdminFeedbackState.set_active_tab("facilitator"),
                ),
                spacing="1",
                border_bottom=f"1px solid {_LINE}",
                width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.icon("info", size=16, color="#6D28D9"),
                    rx.text(
                        rx.cond(
                            AdminFeedbackState.active_tab == "candidate",
                            "Candidate feedback reflects the test experience. Facilitator feedback reflects performance and overall evaluation.",
                            "Facilitator feedback reflects qualitative candidate evaluations and test performance remarks.",
                        ),
                        font_family=FONT_BODY, size="2", color="#4C1D95",
                    ),
                    spacing="2", align_items="center",
                ),
                background="#F5F3FF", border="1px solid #DDD6FE",
                border_radius="8px", padding="0.75em 1.2em", width="100%",
            ),
            spacing="3", width="100%",
        ),
        rx.box(
            rx.cond(
                AdminFeedbackState.active_tab == "candidate",
                rx.hstack(
                    rx.vstack(
                        rx.text("Assessment", size="1", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                        rx.select(AdminFeedbackState.assessment_options, value=AdminFeedbackState.filter_assessment,
                                  on_change=AdminFeedbackState.set_filter_assessment, size="2", width="100%"),
                        spacing="1", flex="1",
                    ),
                    rx.vstack(
                        rx.text("Test", size="1", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                        rx.select(AdminFeedbackState.test_options, value=AdminFeedbackState.filter_test,
                                  on_change=AdminFeedbackState.set_filter_test, size="2", width="100%"),
                        spacing="1", flex="1",
                    ),
                    rx.vstack(
                        rx.text("Candidate", size="1", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                        rx.input(
                            rx.input.slot(rx.icon("search", size=14, color=COLORS["placeholder"])),
                            placeholder="Search candidate...",
                            value=AdminFeedbackState.search_query,
                            on_change=AdminFeedbackState.set_search_query,
                            size="2", width="100%",
                        ),
                        spacing="1", flex="1.4",
                    ),
                    rx.vstack(
                        rx.text("Date Range", size="1", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                        rx.input(
                            rx.input.slot(rx.icon("calendar", size=14, color=COLORS["placeholder"])),
                            placeholder="Select date range",
                            value=AdminFeedbackState.filter_date_range,
                            on_change=AdminFeedbackState.set_filter_date_range,
                            size="2", width="100%",
                        ),
                        spacing="1", flex="1.2",
                    ),
                    rx.vstack(
                        rx.text("", size="1", font_family=FONT_BODY),
                        rx.button(
                            "Reset", variant="outline", color=COLORS["ink"],
                            border=f"1px solid {_LINE}",
                            font_family=FONT_BODY, size="2",
                            _hover={"background": COLORS["canvas"]},
                            on_click=AdminFeedbackState.reset_filters,
                        ),
                        spacing="1",
                    ),
                    spacing="3", align_items="end", width="100%",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("Assessment", size="1", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                        rx.select(AdminFeedbackState.assessment_options, value=AdminFeedbackState.filter_assessment,
                                  on_change=AdminFeedbackState.set_filter_assessment, size="2", width="280px"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("", size="1", font_family=FONT_BODY),
                        rx.button(
                            "Reset", variant="outline", color=COLORS["ink"],
                            border=f"1px solid {_LINE}",
                            font_family=FONT_BODY, size="2",
                            _hover={"background": COLORS["canvas"]},
                            on_click=AdminFeedbackState.reset_filters,
                        ),
                        spacing="1",
                    ),
                    spacing="3", align_items="end", width="100%",
                ),
            ),
            background=COLORS["surface"],
            border=f"1px solid {_LINE}",
            border_radius="10px",
            padding="1.1em 1.4em", width="100%",
        ),
        rx.hstack(
            feedback_table_card(),
            rx.cond(AdminFeedbackState.show_details_panel, feedback_details_panel()),
            spacing="4", width="100%", align_items="start",
        ),
        spacing="4", width="100%", align_items="stretch",
    )
    return admin_shell(
        active="feedback",
        title="Feedback Management",
        subtitle="View and manage feedback from candidates and facilitators across all assessments.",
        content=content,
    )
