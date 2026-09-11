"""
Assessment Workspace — tabbed page for a single assessment.

Tabs (state-based, no route change):
  1. Question Paper  ← built in this feature
  2. Evaluation      ← placeholder (Feature 4)
  3. Results         ← placeholder (Feature 5)
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ──────────────────────────────────────────────────────────────────────────────
# Tab bar
# ──────────────────────────────────────────────────────────────────────────────

def workspace_tab(label: str, icon: str, key: str, active_tab) -> rx.Component:
    """active_tab is a Reflex Var — all conditionals must use rx.cond."""
    is_active = active_tab == key
    return rx.box(
        rx.hstack(
            rx.icon(
                icon,
                size=14,
                color=rx.cond(is_active, COLORS["primary"], COLORS["slate"]),
            ),
            rx.text(
                label,
                font_family=FONT_BODY,
                size="2",
                weight=rx.cond(is_active, "bold", "regular"),
                color=rx.cond(is_active, COLORS["primary"], COLORS["slate"]),
            ),
            spacing="2",
            align_items="center",
        ),
        padding="0.65em 1.2em",
        border_bottom=rx.cond(
            is_active,
            f"2px solid {COLORS['primary']}",
            "2px solid transparent",
        ),
        cursor="pointer",
        on_click=FacilitatorState.set_workspace_tab(key),
        _hover={"border_bottom": f"2px solid {COLORS['line']}"},
    )


def workspace_tab_bar() -> rx.Component:
    return rx.hstack(
        workspace_tab("Question Paper", "file-spreadsheet", "question_paper",
                      FacilitatorState.active_workspace_tab),
        workspace_tab("Evaluation", "pencil-line", "evaluation",
                      FacilitatorState.active_workspace_tab),
        workspace_tab("Results", "bar-chart-2", "results",
                      FacilitatorState.active_workspace_tab),
        spacing="0",
        border_bottom=f"1px solid {COLORS['line']}",
        width="100%",
        padding_bottom="0",
        margin_bottom="1.8em",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Question Paper Tab (Test-wise Upload & Real File Browsing)
# ──────────────────────────────────────────────────────────────────────────────

def test_qp_status_pill(test_name: str, is_final: bool) -> rx.Component:
    """Selectable test button at the top of the Question Paper tab."""
    is_active = FacilitatorState.selected_test_name == test_name
    has_file = FacilitatorState.current_assessment_qp_dict.contains(test_name)
    return rx.box(
        rx.hstack(
            rx.cond(
                is_final,
                rx.icon("award", size=14, color=rx.cond(is_active, "#B45309", COLORS["slate"])),
                rx.icon("file-text", size=14, color=rx.cond(is_active, COLORS["primary"], COLORS["slate"])),
            ),
            rx.vstack(
                rx.text(
                    test_name,
                    font_family=FONT_BODY,
                    size="2",
                    weight=rx.cond(is_active, "bold", "medium"),
                    color=rx.cond(
                        is_active,
                        rx.cond(is_final, "#92400E", COLORS["primary"]),
                        COLORS["ink"],
                    ),
                ),
                rx.cond(
                    has_file,
                    rx.hstack(
                        rx.box(width="6px", height="6px", border_radius="50%", background="#027A48"),
                        rx.text("QP Uploaded", font_family=FONT_BODY, size="1", color="#027A48", weight="medium"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.box(width="6px", height="6px", border_radius="50%", background="#D97706"),
                        rx.text("Pending QP", font_family=FONT_BODY, size="1", color="#D97706"),
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
        padding="0.6em 1em",
        border_radius="10px",
        cursor="pointer",
        background=rx.cond(
            is_active,
            rx.cond(is_final, "#FEF3C7", COLORS["primary_soft"]),
            COLORS["surface"],
        ),
        border=rx.cond(
            is_active,
            rx.cond(is_final, "1.5px solid #F59E0B", f"1.5px solid {COLORS['primary']}"),
            f"1px solid {COLORS['line']}",
        ),
        on_click=FacilitatorState.set_selected_test(test_name),
        _hover={"background": rx.cond(is_active, rx.cond(is_final, "#FEF3C7", COLORS["primary_soft"]), COLORS["canvas"])},
    )


def active_test_uploaded_card() -> rx.Component:
    """Card shown when active test has a question paper uploaded."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("file-spreadsheet", size=26, color="#027A48"),
                    background="#ECFDF3",
                    padding="0.8em",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text(
                        FacilitatorState.current_test_filename,
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.icon("circle-check", size=13, color="#027A48"),
                        rx.text(
                            "Question Paper Uploaded for ", FacilitatorState.selected_test_name,
                            font_family=FONT_BODY,
                            size="1",
                            color="#027A48",
                            weight="medium",
                        ),
                        spacing="1",
                        align_items="center",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(
                        rx.icon("eye", size=13),
                        "View Questions",
                        on_click=FacilitatorState.open_qp_preview(FacilitatorState.selected_test_name, FacilitatorState.selected_assessment_name),
                        size="1",
                        variant="soft",
                        color_scheme="indigo",
                        font_family=FONT_BODY,
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=13),
                        "Replace",
                        on_click=FacilitatorState.start_replacing_qp(FacilitatorState.selected_test_name),
                        size="1",
                        variant="outline",
                        color_scheme="gray",
                        font_family=FONT_BODY,
                    ),
                    rx.button(
                        rx.icon("trash-2", size=13),
                        "Remove",
                        on_click=FacilitatorState.remove_current_test_question_paper,
                        size="1",
                        variant="soft",
                        color_scheme="red",
                        font_family=FONT_BODY,
                    ),
                    spacing="2",
                    align_items="center",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border="1px solid #A6F4C5",
        border_radius="12px",
        padding="1.3em 1.5em",
        width="100%",
    )


def active_test_dropzone_card() -> rx.Component:
    """Browse & Dropzone card for uploading question paper for active test."""
    return rx.box(
        rx.vstack(
            rx.cond(
                FacilitatorState.is_replacing_qp & FacilitatorState.has_current_test_qp,
                rx.hstack(
                    rx.box(
                        rx.icon("info", size=15, color="#B45309"),
                        background="#FEF3C7",
                        padding="0.3em",
                        border_radius="4px",
                    ),
                    rx.text(
                        "Replacing question paper for ", FacilitatorState.selected_test_name, ". Choose a new file to replace the existing one.",
                        font_family=FONT_BODY,
                        size="2",
                        color="#92400E",
                        weight="medium",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=13),
                        "Cancel Replace",
                        on_click=FacilitatorState.cancel_replacing_qp,
                        size="1",
                        variant="outline",
                        color_scheme="gray",
                        font_family=FONT_BODY,
                    ),
                    spacing="2",
                    align_items="center",
                    width="100%",
                    background="#FFFBEB",
                    border="1px solid #FDE68A",
                    padding="0.6em 1em",
                    border_radius="8px",
                    margin_bottom="0.8em",
                ),
            ),
            rx.upload(
                rx.vstack(
                    rx.box(
                        rx.icon("cloud-upload", size=32, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.85em",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.text(
                            "Upload Question Paper for ", FacilitatorState.selected_test_name,
                            font_family=FONT_BODY,
                            size="3",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "Click Browse to select file from your computer or drag & drop here",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                            text_align="center",
                        ),
                        spacing="0",
                        align_items="center",
                    ),
                    rx.button(
                        rx.icon("folder-open", size=15),
                        "Browse File",
                        size="2",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        type="button",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    rx.text(
                        "Supported: .xlsx, .xls, .pdf, .docx, .doc, .csv  ·  Max 10MB",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["placeholder"],
                    ),
                    align_items="center",
                    spacing="2",
                ),
                id="test_qp_file_upload",
                border=f"2px dashed {COLORS['line']}",
                border_radius="12px",
                padding="2em 1.5em",
                background=COLORS["canvas"],
                width="100%",
                cursor="pointer",
                accept={
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                    "application/vnd.ms-excel": [".xls"],
                    "application/pdf": [".pdf"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                    "application/msword": [".doc"],
                    "text/csv": [".csv"],
                },
                max_files=1,
            ),
            # File selection feedback and confirm upload button
            rx.cond(
                rx.selected_files("test_qp_file_upload").length() > 0,
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-check-2", size=18, color="#027A48"),
                            background="#ECFDF3",
                            padding="0.4em",
                            border_radius="6px",
                        ),
                        rx.vstack(
                            rx.text("Selected file ready to upload:", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                            rx.text(
                                rx.selected_files("test_qp_file_upload")[0],
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("upload", size=14),
                            "Upload to ", FacilitatorState.selected_test_name,
                            on_click=FacilitatorState.handle_upload_for_test(rx.upload_files(upload_id="test_qp_file_upload")),
                            size="2",
                            background="#027A48",
                            color="white",
                            font_family=FONT_BODY,
                            _hover={"background": "#05603A"},
                        ),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    background="#ECFDF3",
                    border="1px solid #A6F4C5",
                    border_radius="10px",
                    padding="0.8em 1.2em",
                    width="100%",
                    margin_top="1em",
                ),
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.5em",
        width="100%",
    )


def question_paper_overview_row(test_name: str, is_final: bool) -> rx.Component:
    has_file = FacilitatorState.current_assessment_qp_dict.contains(test_name)
    fname = FacilitatorState.current_assessment_qp_dict.get(test_name, "")
    is_active = FacilitatorState.selected_test_name == test_name
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    is_final,
                    rx.icon("award", size=15, color="#B45309"),
                    rx.icon("file-text", size=15, color=COLORS["primary"]),
                ),
                rx.text(test_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                spacing="2",
                align_items="center",
            )
        ),
        rx.table.cell(
            rx.cond(
                has_file,
                rx.hstack(
                    rx.icon("file-spreadsheet", size=14, color="#027A48"),
                    rx.text(fname, font_family=FONT_BODY, size="2", color=COLORS["ink"], weight="medium"),
                    spacing="1",
                    align_items="center",
                ),
                rx.text("No question paper uploaded", font_family=FONT_BODY, size="2", color=COLORS["placeholder"]),
            )
        ),
        rx.table.cell(
            rx.cond(
                has_file,
                rx.badge("Uploaded", color_scheme="green", variant="soft", size="1", font_family=FONT_BODY),
                rx.badge("Pending", color_scheme="orange", variant="soft", size="1", font_family=FONT_BODY),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    has_file,
                    rx.button(
                        rx.icon("eye", size=12),
                        "View",
                        on_click=FacilitatorState.open_qp_preview(test_name, FacilitatorState.selected_assessment_name),
                        size="1",
                        variant="soft",
                        color_scheme="indigo",
                        font_family=FONT_BODY,
                    ),
                ),
                rx.button(
                    rx.cond(has_file, "Replace", "Browse & Upload"),
                    on_click=FacilitatorState.start_replacing_qp(test_name),
                    size="1",
                    variant=rx.cond(is_active, "solid", "outline"),
                    color_scheme=rx.cond(is_final, "amber", "indigo"),
                    font_family=FONT_BODY,
                ),
                rx.cond(
                    has_file,
                    rx.button(
                        rx.icon("trash-2", size=12),
                        on_click=FacilitatorState.remove_test_question_paper(test_name),
                        size="1",
                        variant="ghost",
                        color=COLORS["danger"],
                        _hover={"background": "#FEE4E2"},
                    ),
                ),
                spacing="2",
                align_items="center",
            )
        ),
    )


def test_management_card(test: dict) -> rx.Component:
    t_name = test["name"]
    t_date = test["date"]
    is_final = test["is_final"]
    has_file = test["has_qp"]
    is_active = FacilitatorState.selected_test_name == t_name

    return rx.box(
        rx.hstack(
            # Left: Icon & Info
            rx.hstack(
                rx.box(
                    rx.cond(
                        is_final,
                        rx.icon("award", size=20, color="#D97706"),
                        rx.icon("file-text", size=20, color=COLORS["primary"]),
                    ),
                    background=rx.cond(
                        is_final,
                        "#FEF3C7",
                        "#EDE9FE",
                    ),
                    padding="0.65em",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink=0,
                ),
                rx.vstack(
                    rx.text(
                        t_name,
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.icon("calendar", size=13, color=COLORS["slate"]),
                        rx.vstack(
                            rx.text("Test Date", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                            rx.text(
                                rx.cond(t_date != "", t_date, "Not scheduled"),
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="2",
                        align_items="start",
                        padding_top="0.3em",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="start",
            ),
            rx.spacer(),
            # Right: Status badge & Actions
            rx.vstack(
                rx.hstack(
                    rx.cond(
                        has_file,
                        rx.badge(
                            rx.hstack(
                                rx.icon("circle-check", size=12),
                                rx.text("Question Paper Uploaded"),
                                spacing="1",
                                align_items="center",
                            ),
                            color_scheme="green",
                            variant="soft",
                            size="1",
                            border_radius="12px",
                            padding="0.3em 0.7em",
                        ),
                        rx.badge(
                            rx.hstack(
                                rx.icon("clock", size=12),
                                rx.text("Pending Question Paper"),
                                spacing="1",
                                align_items="center",
                            ),
                            color_scheme="amber",
                            variant="soft",
                            size="1",
                            border_radius="12px",
                            padding="0.3em 0.7em",
                        ),
                    ),
                    rx.menu.root(
                        rx.menu.trigger(
                            rx.icon_button(
                                rx.icon("ellipsis-vertical", size=14),
                                variant="ghost",
                                color_scheme="gray",
                                size="1",
                                cursor="pointer",
                            ),
                        ),
                        rx.menu.content(
                            rx.cond(
                                has_file,
                                rx.menu.item(
                                    "View Question Paper",
                                    on_click=FacilitatorState.open_qp_preview(t_name, FacilitatorState.selected_assessment_name),
                                ),
                            ),
                            rx.menu.item(
                                rx.cond(has_file, "Replace Question Paper", "Upload Question Paper"),
                                on_click=FacilitatorState.start_replacing_qp(t_name),
                            ),
                            rx.cond(
                                has_file,
                                rx.menu.item(
                                    "Remove Question Paper",
                                    on_click=FacilitatorState.remove_test_question_paper(t_name),
                                    color="red",
                                ),
                            ),
                            rx.menu.separator(),
                            rx.menu.item(
                                "Delete Test",
                                on_click=FacilitatorState.facilitator_remove_test(t_name),
                                color="red",
                            ),
                        ),
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.button(
                    "Manage",
                    rx.icon("arrow-right", size=13),
                    on_click=FacilitatorState.set_selected_test(t_name),
                    size="1",
                    variant="outline",
                    color_scheme="gray",
                    font_family=FONT_BODY,
                    border_radius="6px",
                    margin_top="0.8em",
                    cursor="pointer",
                ),
                align_items="end",
                spacing="0",
            ),
            width="100%",
            align_items="start",
        ),
        padding="1.1em 1.3em",
        border_radius="12px",
        background=rx.cond(is_active, "#FAFAFE", COLORS["surface"]),
        border=rx.cond(
            is_active,
            f"1.5px solid {COLORS['primary']}",
            f"1px solid {COLORS['line']}",
        ),
        cursor="pointer",
        on_click=FacilitatorState.set_selected_test(t_name),
        _hover={
            "border_color": rx.cond(is_active, COLORS["primary"], "#CBD5E1"),
            "background": rx.cond(is_active, "#FAFAFE", "#FAFAFC"),
        },
        transition="all 0.15s ease",
        width="100%",
    )


def test_management_left_column() -> rx.Component:
    assessment = FacilitatorState.my_assessments[FacilitatorState.selected_assessment_index]
    test_items = assessment["test_items"]

    return rx.vstack(
        # Section Header
        rx.hstack(
            rx.vstack(
                rx.text(
                    "Test Management",
                    font_family=FONT_DISPLAY,
                    size="4",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.text(
                    "Create and manage tests for this assessment.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                rx.text(
                    "Select a test to upload or replace its question paper.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="0",
                align_items="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("plus", size=14),
                "Add Test",
                on_click=FacilitatorState.open_add_test_modal,
                size="2",
                background=COLORS["primary"],
                color="white",
                font_family=FONT_BODY,
                border_radius="8px",
                _hover={"background": COLORS["primary_hover"]},
                cursor="pointer",
            ),
            width="100%",
            align_items="start",
            padding_bottom="0.5em",
        ),
        # Cards List
        rx.vstack(
            rx.foreach(
                test_items,
                test_management_card,
            ),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
        align_items="stretch",
    )


def question_paper_right_column() -> rx.Component:
    return rx.vstack(
        # ── Top Card (Selected Test Summary) ──
        rx.hstack(
            rx.hstack(
                rx.box(
                    rx.cond(
                        FacilitatorState.is_selected_test_summative,
                        rx.icon("award", size=22, color="#D97706"),
                        rx.icon("file-text", size=22, color=COLORS["primary"]),
                    ),
                    background=rx.cond(
                        FacilitatorState.is_selected_test_summative,
                        "#FEF3C7",
                        "#EDE9FE",
                    ),
                    padding="0.65em",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text(
                        FacilitatorState.selected_test_name,
                        font_family=FONT_DISPLAY,
                        size="4",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.text(
                            "Test Date: ",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        rx.text(
                            rx.cond(
                                FacilitatorState.current_selected_test_date != "",
                                FacilitatorState.current_selected_test_date,
                                "Not scheduled",
                            ),
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color=COLORS["ink"],
                        ),
                        spacing="1",
                        align_items="center",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    FacilitatorState.has_current_test_qp,
                    rx.badge(
                        rx.hstack(
                            rx.icon("circle-check", size=13),
                            rx.text("Question Paper Uploaded"),
                            spacing="1",
                            align_items="center",
                        ),
                        color_scheme="green",
                        variant="soft",
                        size="2",
                        border_radius="16px",
                        padding="0.3em 0.8em",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.icon("clock", size=13),
                            rx.text("Pending Question Paper"),
                            spacing="1",
                            align_items="center",
                        ),
                        color_scheme="amber",
                        variant="soft",
                        size="2",
                        border_radius="16px",
                        padding="0.3em 0.8em",
                    ),
                ),
                rx.menu.root(
                    rx.menu.trigger(
                        rx.icon_button(
                            rx.icon("ellipsis-vertical", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                        ),
                    ),
                    rx.menu.content(
                        rx.cond(
                            FacilitatorState.has_current_test_qp,
                            rx.menu.item(
                                "View File",
                                on_click=FacilitatorState.open_qp_preview(FacilitatorState.selected_test_name, FacilitatorState.selected_assessment_name),
                            ),
                        ),
                        rx.menu.item(
                            rx.cond(FacilitatorState.has_current_test_qp, "Replace File", "Upload File"),
                            on_click=FacilitatorState.start_replacing_qp(FacilitatorState.selected_test_name),
                        ),
                        rx.cond(
                            FacilitatorState.has_current_test_qp,
                            rx.menu.item(
                                "Remove Question Paper",
                                on_click=FacilitatorState.remove_current_test_question_paper,
                                color="red",
                            ),
                        ),
                        rx.menu.separator(),
                        rx.menu.item(
                            "Delete Test",
                            on_click=FacilitatorState.facilitator_remove_test(FacilitatorState.selected_test_name),
                            color="red",
                        ),
                    ),
                ),
                spacing="2",
                align_items="center",
            ),
            width="100%",
            align_items="center",
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.1em 1.4em",
        ),

        # ── Question Paper Section ──
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=16, color=COLORS["ink"]),
                rx.text(
                    "Question Paper",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                padding_top="0.6em",
            ),
            # Content Card
            rx.cond(
                FacilitatorState.has_current_test_qp & ~FacilitatorState.is_replacing_qp,
                # Uploaded Card View
                rx.box(
                    rx.vstack(
                        rx.box(
                            rx.icon("cloud-upload", size=30, color="#7C3AED"),
                            background="#F5F3FF",
                            padding="0.9em",
                            border_radius="50%",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.text(
                            "Question Paper Uploaded",
                            font_family=FONT_BODY,
                            size="3",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.hstack(
                            rx.text(
                                FacilitatorState.current_test_filename,
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                                weight="medium",
                            ),
                            rx.text(
                                "(2.4 MB)",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["placeholder"],
                            ),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.button(
                                rx.icon("eye", size=14),
                                "View File",
                                variant="outline",
                                color_scheme="gray",
                                font_family=FONT_BODY,
                                size="2",
                                border_radius="8px",
                                on_click=FacilitatorState.open_qp_preview(FacilitatorState.selected_test_name, FacilitatorState.selected_assessment_name),
                                cursor="pointer",
                            ),
                            rx.button(
                                rx.icon("refresh-cw", size=14),
                                "Replace File",
                                background=COLORS["primary"],
                                color="white",
                                font_family=FONT_BODY,
                                size="2",
                                border_radius="8px",
                                on_click=FacilitatorState.start_replacing_qp(FacilitatorState.selected_test_name),
                                _hover={"background": COLORS["primary_hover"]},
                                cursor="pointer",
                            ),
                            spacing="3",
                            align_items="center",
                            padding_top="0.5em",
                        ),
                        rx.text(
                            "Supported formats: .xlsx, .xls, .pdf, .docx, .doc, .csv  •  Max size: 10MB",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["placeholder"],
                            padding_top="0.8em",
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                        padding="3.5em 2em",
                    ),
                    border=f"1.5px dashed {COLORS['line']}",
                    border_radius="14px",
                    background="#FAFAFC",
                    width="100%",
                ),
                # Dropzone View (when pending or replacing)
                rx.box(
                    rx.vstack(
                        rx.cond(
                            FacilitatorState.is_replacing_qp,
                            rx.hstack(
                                rx.text(
                                    "Replacing file for ", FacilitatorState.selected_test_name,
                                    font_family=FONT_BODY,
                                    size="2",
                                    color="#92400E",
                                ),
                                rx.spacer(),
                                rx.button(
                                    "Cancel",
                                    size="1",
                                    variant="ghost",
                                    on_click=FacilitatorState.cancel_replacing_qp,
                                ),
                                width="100%",
                                background="#FFFBEB",
                                padding="0.4em 0.8em",
                                border_radius="6px",
                            ),
                        ),
                        rx.upload(
                            rx.vstack(
                                rx.box(
                                    rx.icon("cloud-upload", size=30, color=COLORS["primary"]),
                                    background="#F5F3FF",
                                    padding="0.9em",
                                    border_radius="50%",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                ),
                                rx.text(
                                    "Upload Question Paper for ", FacilitatorState.selected_test_name,
                                    font_family=FONT_BODY,
                                    size="3",
                                    weight="bold",
                                    color=COLORS["ink"],
                                ),
                                rx.text(
                                    "Drag & drop file here or click Browse File",
                                    font_family=FONT_BODY,
                                    size="2",
                                    color=COLORS["slate"],
                                ),
                                rx.button(
                                    rx.icon("folder-open", size=14),
                                    "Browse File",
                                    variant="outline",
                                    color_scheme="indigo",
                                    font_family=FONT_BODY,
                                    size="2",
                                    border_radius="8px",
                                    cursor="pointer",
                                ),
                                rx.text(
                                    "Supported formats: .xlsx, .xls, .pdf, .docx, .doc, .csv  •  Max size: 10MB",
                                    font_family=FONT_BODY,
                                    size="1",
                                    color=COLORS["placeholder"],
                                    padding_top="0.5em",
                                ),
                                spacing="2",
                                align_items="center",
                                width="100%",
                            ),
                            id="test_qp_file_upload",
                            padding="3.5em 2em",
                            width="100%",
                        ),
                        rx.cond(
                            rx.selected_files("test_qp_file_upload"),
                            rx.hstack(
                                rx.foreach(
                                    rx.selected_files("test_qp_file_upload"),
                                    lambda f: rx.badge(f, color_scheme="indigo", size="2"),
                                ),
                                rx.spacer(),
                                rx.button(
                                    rx.icon("upload", size=14),
                                    "Confirm Upload",
                                    on_click=FacilitatorState.handle_upload_for_test(rx.upload_files(upload_id="test_qp_file_upload")),
                                    background="#027A48",
                                    color="white",
                                    size="2",
                                    border_radius="8px",
                                    _hover={"background": "#05603A"},
                                ),
                                spacing="2",
                                width="100%",
                                padding="0.8em 1.2em",
                                background="#ECFDF3",
                                border_radius="8px",
                                align_items="center",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    border=f"1.5px dashed {COLORS['line']}",
                    border_radius="14px",
                    background="#FAFAFC",
                    width="100%",
                ),
            ),
            # Status Banner
            rx.cond(
                FacilitatorState.has_current_test_qp,
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=20, color="#027A48"),
                        rx.vstack(
                            rx.text(
                                "Question paper is ready for evaluation.",
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color="#027A48",
                            ),
                            rx.text(
                                "You can replace the file if needed.",
                                font_family=FONT_BODY,
                                size="1",
                                color="#027A48",
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#ECFDF3",
                    border="1px solid #A6F4C5",
                    border_radius="10px",
                    padding="0.9em 1.2em",
                    width="100%",
                ),
                rx.box(
                    rx.hstack(
                        rx.icon("clock", size=20, color="#B45309"),
                        rx.vstack(
                            rx.text(
                                "Question paper pending upload.",
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color="#92400E",
                            ),
                            rx.text(
                                "Upload a question paper above so candidates can take this test.",
                                font_family=FONT_BODY,
                                size="1",
                                color="#92400E",
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#FFFBEB",
                    border="1px solid #FDE68A",
                    border_radius="10px",
                    padding="0.9em 1.2em",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )


def question_paper_tab() -> rx.Component:
    assessment = FacilitatorState.my_assessments[FacilitatorState.selected_assessment_index]
    test_items = assessment["test_items"]

    # When no tests configured
    empty_state = rx.center(
        rx.vstack(
            rx.box(
                rx.icon("layers", size=36, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="1.2em",
                border_radius="50%",
            ),
            rx.text("No tests yet", font_family=FONT_DISPLAY, size="4", weight="bold", color=COLORS["ink"]),
            rx.text("Get started by adding tests to this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
            rx.button(
                rx.icon("plus", size=14),
                "Add Test",
                on_click=FacilitatorState.open_add_test_modal,
                size="2",
                background=COLORS["primary"],
                color="white",
                font_family=FONT_BODY,
                border_radius="8px",
                _hover={"background": COLORS["primary_hover"]},
                margin_top="0.5em",
                cursor="pointer",
            ),
            align_items="center",
            spacing="2",
            padding="4em 2em",
        ),
        width="100%",
        background=COLORS["surface"],
        border=f"1.5px dashed {COLORS['line']}",
        border_radius="16px",
    )

    two_column_view = rx.grid(
        # Left column: Test Management & Cards
        test_management_left_column(),
        # Right column: Question Paper Details for active test
        rx.cond(
            FacilitatorState.selected_test_name != "",
            question_paper_right_column(),
            rx.center(
                rx.text("Select a test on the left to view its Question Paper details.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                padding="4em 2em",
                width="100%",
            ),
        ),
        columns="5fr 6fr",
        gap="1.8em",
        width="100%",
        align_items="start",
    )

    return rx.cond(
        test_items.length() > 0,
        two_column_view,
        empty_state,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation Tab Components (Visually matching reference design)
# ──────────────────────────────────────────────────────────────────────────────

def evaluation_test_header() -> rx.Component:
    return rx.hstack(
        # Left: Test info
        rx.vstack(
            rx.text("Test:", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
            rx.text(
                FacilitatorState.selected_test_name,
                font_family=FONT_DISPLAY,
                size="6",
                weight="bold",
                color=COLORS["ink"],
            ),
            spacing="0",
            align_items="start",
        ),
        width="100%",
        align_items="center",
        padding_bottom="1.5em",
    )


def evaluation_candidate_selection_card() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: Select Candidate Dropdown
            rx.vstack(
                rx.text("Select Candidate", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                rx.select(
                    FacilitatorState.evaluation_candidate_options,
                    value=FacilitatorState.selected_evaluation_candidate,
                    on_change=FacilitatorState.set_selected_evaluation_candidate,
                    size="2",
                    width="100%",
                    min_width="220px",
                ),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            # Right: Submission Status & Timestamp
            rx.vstack(
                rx.hstack(
                    rx.text("Submission Status", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.badge("Submitted", color_scheme="green", variant="soft", size="1"),
                    spacing="2",
                    align_items="center",
                ),
                rx.vstack(
                    rx.text("Submitted On", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(
                        FacilitatorState.current_candidate_submitted_on,
                        font_family=FONT_BODY,
                        size="2",
                        weight="medium",
                        color=COLORS["ink"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="1",
                align_items="start",
                min_width="160px",
            ),
            spacing="4",
            width="100%",
            align_items="center",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em 1.5em",
        width="100%",
        margin_bottom="1.2em",
    )


def evaluation_files_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "Evaluation Files",
                font_family=FONT_BODY,
                size="3",
                weight="bold",
                color=COLORS["ink"],
                padding_bottom="0.4em",
            ),

            # Row 1: Question Paper
            rx.hstack(
                rx.box(
                    rx.icon("file-spreadsheet", size=18, color="#027A48"),
                    background="#ECFDF3",
                    padding="0.5em",
                    border_radius="8px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("Question Paper", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    rx.text(FacilitatorState.eval_qp_filename, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.badge("Available", color_scheme="green", variant="soft", size="1"),
                rx.button(
                    rx.icon("eye", size=13),
                    "View File",
                    on_click=FacilitatorState.open_qp_preview(FacilitatorState.selected_test_name, FacilitatorState.selected_assessment_name),
                    size="1",
                    variant="soft",
                    color_scheme="indigo",
                    font_family=FONT_BODY,
                ),
                spacing="3",
                align_items="center",
                width="100%",
                padding_y="0.6em",
            ),

            rx.divider(color_scheme="gray", size="4"),

            # Row 2: Candidate Response
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=18, color=COLORS["primary"]),
                    background=COLORS["primary_soft"],
                    padding="0.5em",
                    border_radius="8px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("Candidate Response", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    rx.text(
                        FacilitatorState.current_candidate_excel_file,
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.cond(
                    FacilitatorState.has_submitted_response,
                    rx.badge("Submitted", color_scheme="green", variant="soft", size="1"),
                    rx.badge("Not Submitted", color_scheme="gray", variant="soft", size="1"),
                ),
                rx.button(
                    rx.icon("eye", size=13),
                    "View Response",
                    on_click=FacilitatorState.open_candidate_response_modal,
                    size="1",
                    variant="soft",
                    color_scheme="indigo",
                    font_family=FONT_BODY,
                ),
                rx.button(
                    rx.icon("download", size=13),
                    "Download Excel",
                    on_click=FacilitatorState.download_candidate_response,
                    size="1",
                    variant="outline",
                    color_scheme="gray",
                    font_family=FONT_BODY,
                    disabled=~FacilitatorState.has_submitted_response,
                ),
                spacing="2",
                align_items="center",
                width="100%",
                padding_y="0.6em",
            ),

            # Information Banner
            rx.box(
                rx.hstack(
                    rx.icon("info", size=16, color="#175CD3"),
                    rx.text(
                        "Candidate response is stored in Excel format for easy viewing and evaluation.",
                        font_family=FONT_BODY,
                        size="1",
                        color="#175CD3",
                        weight="medium",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                background="#EFF8FF",
                border="1px solid #B2DDFF",
                border_radius="8px",
                padding="0.7em 1em",
                width="100%",
                margin_top="0.8em",
            ),

            spacing="1",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.5em",
        width="100%",
    )


def evaluation_left_column() -> rx.Component:
    return rx.vstack(
        evaluation_candidate_selection_card(),
        evaluation_files_card(),
        spacing="0",
        flex="1",
        width="50%",
        align_items="stretch",
    )


def evaluation_methods_card() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.text(
                "Evaluation Method",
                font_family=FONT_BODY,
                size="3",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "Choose the evaluation method you want to use for this candidate.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            spacing="0",
            align_items="start",
            padding_bottom="0.8em",
        ),
        rx.hstack(
            # Card 1: Manual Evaluation
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.icon("pencil", size=22, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.85em",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text("Manual Evaluation", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                    rx.text(
                        "Evaluate candidate response yourself, question by question.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                        text_align="center",
                        min_height="36px",
                    ),
                    rx.button(
                        rx.icon("clipboard-pen", size=14),
                        "Start Manual Evaluation",
                        on_click=FacilitatorState.open_manual_eval_modal,
                        size="2",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        width="100%",
                        border_radius="8px",
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="12px",
                padding="1.6em 1.2em",
                flex="1",
            ),
            # Card 2: AI Evaluation
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.icon("sparkles", size=22, color="#027A48"),
                        background="#ECFDF3",
                        padding="0.85em",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text("AI Evaluation", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                    rx.text(
                        "Evaluate using AI engine with answer key and scoring criteria.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                        text_align="center",
                        min_height="36px",
                    ),
                    rx.button(
                        rx.icon("plus", size=14),
                        "Start AI Evaluation",
                        on_click=FacilitatorState.open_ai_eval_modal,
                        size="2",
                        background="#027A48",
                        color="white",
                        font_family=FONT_BODY,
                        width="100%",
                        border_radius="8px",
                        _hover={"background": "#05603A"},
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="12px",
                padding="1.6em 1.2em",
                flex="1",
            ),
            spacing="3",
            width="100%",
        ),
        spacing="0",
        width="100%",
        align_items="stretch",
    )


def evaluation_ai_results_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header Row
            rx.hstack(
                rx.text(
                    rx.cond(
                        FacilitatorState.real_ai_score_display != "—",
                        "AI Evaluation Results",
                        "AI Evaluation Results (Mock)",
                    ),
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("download", size=13),
                    "Download Report",
                    on_click=FacilitatorState.download_ai_eval_report,
                    size="1",
                    variant="outline",
                    color_scheme="indigo",
                    font_family=FONT_BODY,
                ),
                width="100%",
                align_items="center",
                padding_bottom="0.4em",
            ),

            # Status Alert Banner
            rx.box(
                rx.hstack(
                    rx.cond(
                        FacilitatorState.has_ai_evaluated_current_candidate,
                        rx.icon("circle-check", size=15, color="#027A48"),
                        rx.icon("clock", size=15, color=COLORS["slate"]),
                    ),
                    rx.text(
                        rx.cond(
                            FacilitatorState.has_ai_evaluated_current_candidate,
                            "AI evaluation completed successfully",
                            rx.cond(
                                FacilitatorState.has_submitted_response,
                                "Candidate response submitted — Ready for AI Evaluation",
                                "No response submitted yet",
                            ),
                        ),
                        font_family=FONT_BODY,
                        size="1",
                        color=rx.cond(FacilitatorState.has_ai_evaluated_current_candidate, "#027A48", COLORS["slate"]),
                        weight="medium",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                background=rx.cond(FacilitatorState.has_ai_evaluated_current_candidate, "#ECFDF3", COLORS["canvas"]),
                border=rx.cond(FacilitatorState.has_ai_evaluated_current_candidate, "1px solid #A6F4C5", f"1px solid {COLORS['line']}"),
                border_radius="8px",
                padding="0.6em 0.9em",
                width="100%",
                margin_bottom="0.8em",
            ),

            # 3 Score Metric Cards
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.text("Total Score", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        rx.text(
                            FacilitatorState.current_candidate_ai_score_display,
                            font_family=FONT_DISPLAY,
                            size="4",
                            weight="bold",
                            color="#027A48",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    padding="0.8em 1em",
                    flex="1",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Percentage", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        rx.text(
                            FacilitatorState.current_candidate_ai_percentage_display,
                            font_family=FONT_DISPLAY,
                            size="4",
                            weight="bold",
                            color="#2563EB",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    padding="0.8em 1em",
                    flex="1",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Evaluation Date", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        rx.text(
                            FacilitatorState.current_candidate_ai_eval_date,
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color=COLORS["ink"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    padding="0.8em 1em",
                    flex="1",
                ),
                spacing="3",
                width="100%",
                margin_bottom="0.8em",
            ),

            # Question-wise Breakdown Table
            rx.cond(
                FacilitatorState.has_ai_evaluated_current_candidate,
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("Question No.", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="90px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("AI Score", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="75px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Max Marks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="85px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("AI Justification", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                ),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                FacilitatorState.current_candidate_ai_eval_questions,
                                lambda q: rx.table.row(
                                    rx.table.cell(
                                        rx.text(q["q_no"], font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"]),
                                        vertical_align="top",
                                    ),
                                    rx.table.cell(
                                        rx.text(q["ai_score"], font_family=FONT_BODY, size="1", color=COLORS["ink"]),
                                        vertical_align="top",
                                    ),
                                    rx.table.cell(
                                        rx.text(q["max_marks"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                        vertical_align="top",
                                    ),
                                    rx.table.cell(
                                        rx.text(q["justification"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                        vertical_align="top",
                                    ),
                                ),
                            ),
                            # Total Summary Row
                            rx.table.row(
                                rx.table.cell(rx.text("Total", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(rx.text(FacilitatorState.current_candidate_ai_total_score_only, font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(rx.text(FacilitatorState.current_candidate_ai_max_val, font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(rx.text("", font_family=FONT_BODY, size="1")),
                                background="#F9FAFB",
                            ),
                        ),
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    overflow="hidden",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon("sparkles", size=24, color=COLORS["slate"]),
                        rx.text("No AI evaluation results yet", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                        rx.text(
                            rx.cond(
                                FacilitatorState.has_submitted_response,
                                "Click 'Start AI Evaluation' above to run real AI evaluation for this candidate.",
                                "Candidate has not submitted a response for evaluation.",
                            ),
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                            text_align="center",
                        ),
                        spacing="1",
                        align_items="center",
                        justify_content="center",
                        padding="2.5em 1em",
                        width="100%",
                    ),
                    border=f"1px dashed {COLORS['line']}",
                    border_radius="8px",
                    width="100%",
                    background=COLORS["canvas"],
                ),
            ),

            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.5em",
        width="100%",
        margin_top="1.2em",
    )


def evaluation_right_column() -> rx.Component:
    return rx.vstack(
        evaluation_methods_card(),
        evaluation_ai_results_card(),
        spacing="0",
        flex="1",
        width="50%",
        align_items="stretch",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation Tab Modals (Candidate Response, Manual Eval, Answer Key, AI Eval)
# ──────────────────────────────────────────────────────────────────────────────

def candidate_response_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.text(
                        "Candidate Response - " + FacilitatorState.selected_evaluation_candidate,
                        font_family=FONT_BODY,
                        size="4",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Content: Table if submitted, else Empty State
                rx.cond(
                    FacilitatorState.has_submitted_response,
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        rx.text("Question No.", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]),
                                        width="110px",
                                        min_width="110px",
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Question", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]),
                                        width="280px",
                                        min_width="240px",
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Candidate Response", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]),
                                    ),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    FacilitatorState.current_candidate_responses,
                                    lambda item: rx.table.row(
                                        rx.table.cell(
                                            rx.text(item["q_no"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                            vertical_align="top",
                                        ),
                                        rx.table.cell(
                                            rx.text(item["question"], font_family=FONT_BODY, size="2", color=COLORS["ink"]),
                                            vertical_align="top",
                                        ),
                                        rx.table.cell(
                                            rx.text(item["response"], font_family=FONT_BODY, size="2", color=COLORS["slate"], line_height="1.5"),
                                            vertical_align="top",
                                        ),
                                    ),
                                ),
                            ),
                            width="100%",
                        ),
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        overflow="auto",
                        max_height="420px",
                        width="100%",
                        margin_y="1em",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.icon("file-x", size=36, color=COLORS["slate"]),
                            rx.text(
                                "No Response Available",
                                font_family=FONT_BODY,
                                size="3",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "This candidate has not submitted any response for this test.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                            ),
                            spacing="2",
                            align_items="center",
                            justify_content="center",
                            padding="3.5em 1.5em",
                            width="100%",
                        ),
                        border=f"1px dashed {COLORS['line']}",
                        border_radius="10px",
                        margin_y="1em",
                        width="100%",
                        background=COLORS["canvas"],
                    ),
                ),

                # Footer Action Buttons
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                    ),
                    rx.cond(
                        FacilitatorState.has_submitted_response,
                        rx.button(
                            rx.icon("download", size=14),
                            "Download Excel",
                            on_click=FacilitatorState.download_candidate_response,
                            variant="outline",
                            color_scheme="indigo",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),

                spacing="0",
                width="100%",
            ),
            style={"maxWidth": "860px", "width": "90vw"},
            padding="1.8em",
            border_radius="14px",
        ),
        open=FacilitatorState.show_candidate_response_modal,
        on_open_change=FacilitatorState.set_show_candidate_response_modal,
    )


def manual_evaluation_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.box(
                        rx.icon("pencil", size=20, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.5em",
                        border_radius="8px",
                    ),
                    rx.vstack(
                        rx.dialog.title("Manual Evaluation — " + FacilitatorState.selected_evaluation_candidate),
                        rx.text(
                            "Question " + (FacilitatorState.manual_eval_q_index + 1).to_string() + " of 4",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                            weight="bold",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom=f"1px solid {COLORS['line']}",
                ),

                # Question & Response Section
                rx.box(
                    rx.vstack(
                        rx.text("Question:", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                        rx.text(
                            FacilitatorState.current_manual_question_text,
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text("Candidate Response:", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], padding_top="0.6em"),
                        rx.box(
                            rx.text(
                                FacilitatorState.current_manual_response_text,
                                font_family=FONT_BODY,
                                size="2",
                                color="#374151",
                                line_height="1.5",
                            ),
                            background="#F9FAFB",
                            border=f"1px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.8em 1em",
                            width="100%",
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    padding_y="0.8em",
                    width="100%",
                ),

                # Marks Input
                rx.hstack(
                    rx.vstack(
                        rx.text("Award Marks (Max 5)", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"]),
                        rx.input(
                            value=FacilitatorState.current_manual_mark_val,
                            on_change=FacilitatorState.set_current_manual_mark,
                            placeholder="e.g. 4",
                            type="number",
                            size="2",
                            width="140px",
                        ),
                        spacing="1",
                        align_items="start",
                    ),
                    rx.spacer(),
                    spacing="3",
                    width="100%",
                ),

                # Justification Area
                rx.vstack(
                    rx.text("Evaluation Justification / Remarks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"], padding_top="0.5em"),
                    rx.text_area(
                        value=FacilitatorState.current_manual_justification_val,
                        on_change=FacilitatorState.set_current_manual_justification,
                        placeholder="Enter evaluation remarks explaining the marks awarded...",
                        size="2",
                        width="100%",
                        min_height="80px",
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),

                # Navigation & Save Buttons
                rx.hstack(
                    rx.button(
                        rx.icon("arrow-left", size=13),
                        "Previous Question",
                        on_click=FacilitatorState.prev_manual_question,
                        disabled=FacilitatorState.manual_eval_q_index == 0,
                        variant="outline",
                        color_scheme="gray",
                        size="2",
                        font_family=FONT_BODY,
                    ),
                    rx.button(
                        "Next Question",
                        rx.icon("arrow-right", size=13),
                        on_click=FacilitatorState.next_manual_question,
                        disabled=FacilitatorState.manual_eval_q_index == 3,
                        variant="outline",
                        color_scheme="gray",
                        size="2",
                        font_family=FONT_BODY,
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("check", size=14),
                        "Save Evaluation",
                        on_click=FacilitatorState.save_manual_evaluation,
                        background=COLORS["primary"],
                        color="white",
                        size="2",
                        font_family=FONT_BODY,
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    spacing="2",
                    align_items="center",
                    width="100%",
                    padding_top="1.2em",
                ),

                spacing="2",
                width="100%",
            ),
            style={"maxWidth": "620px", "width": "90vw"},
            padding="1.8em",
            border_radius="14px",
        ),
        open=FacilitatorState.show_manual_eval_modal,
        on_open_change=FacilitatorState.set_show_manual_eval_modal,
    )


def answer_key_upload_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("award", size=20, color="#B54708"),
                        background="#FFFAEB",
                        padding="0.5em",
                        border_radius="8px",
                    ),
                    rx.dialog.title("Upload Model Answer Key"),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align_items="center",
                ),
                rx.dialog.description(
                    "Upload the official model answer key Excel or PDF file for benchmarking candidate responses.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                rx.upload(
                    rx.vstack(
                        rx.icon("file-spreadsheet", size=32, color="#B54708"),
                        rx.text("Click to select answer key (.xlsx, .xls)", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                        rx.button(
                            "Browse File",
                            size="2",
                            background="#B54708",
                            color="white",
                            font_family=FONT_BODY,
                            type="button",
                        ),
                        spacing="2",
                        align_items="center",
                        padding="2em",
                        width="100%",
                    ),
                    id="answer_key_upload_zone",
                    accept={
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                        "application/vnd.ms-excel": [".xls"],
                    },
                    max_files=1,
                    border=f"2px dashed {COLORS['line']}",
                    border_radius="10px",
                    background=COLORS["canvas"],
                    width="100%",
                    margin_y="1em",
                    cursor="pointer",
                ),
                rx.cond(
                    rx.selected_files("answer_key_upload_zone").length() > 0,
                    rx.hstack(
                        rx.icon("file-check-2", size=16, color="#027A48"),
                        rx.text(
                            rx.selected_files("answer_key_upload_zone")[0],
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("upload", size=14),
                            "Upload",
                            on_click=FacilitatorState.handle_answer_key_upload(rx.upload_files(upload_id="answer_key_upload_zone")),
                            size="2",
                            background="#027A48",
                            color="white",
                            font_family=FONT_BODY,
                        ),
                        spacing="2",
                        align_items="center",
                        background="#ECFDF3",
                        border="1px solid #A6F4C5",
                        border_radius="8px",
                        padding="0.6em 1em",
                        width="100%",
                        margin_bottom="0.5em",
                    ),
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color_scheme="gray",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                    ),
                    rx.button(
                        "Set Default Key (Mock)",
                        on_click=FacilitatorState.simulate_upload_answer_key,
                        background="#027A48",
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            max_width="480px",
            padding="1.8em",
            border_radius="14px",
        ),
        open=FacilitatorState.show_answer_key_upload_modal,
        on_open_change=FacilitatorState.set_show_answer_key_upload_modal,
    )


def ai_evaluation_trigger_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("sparkles", size=20, color="#027A48"),
                        background="#ECFDF3",
                        padding="0.5em",
                        border_radius="8px",
                    ),
                    rx.dialog.title("Start AI Hybrid Evaluation"),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align_items="center",
                ),
                rx.dialog.description(
                    "AI evaluation verifies candidate answers against model criteria and generates score justifications.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),

                # Readiness checklist
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("circle-check", size=16, color="#027A48"),
                            rx.text("Question Paper: ", FacilitatorState.eval_qp_filename, font_family=FONT_BODY, size="2", color=COLORS["ink"]),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.icon("circle-check", size=16, color="#027A48"),
                            rx.text("Answer Key: Verified Benchmarks", font_family=FONT_BODY, size="2", color=COLORS["ink"]),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.icon("circle-check", size=16, color="#027A48"),
                            rx.text("Candidate Response: " + FacilitatorState.selected_evaluation_candidate, font_family=FONT_BODY, size="2", color=COLORS["ink"]),
                            spacing="2",
                            align_items="center",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background="#F0FDF4",
                    border="1px solid #BBF7D0",
                    border_radius="8px",
                    padding="1em",
                    margin_y="1em",
                    width="100%",
                ),

                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button("Cancel", variant="outline", color_scheme="gray", size="2"),
                    ),
                    rx.button(
                        rx.icon("sparkles", size=14),
                        "Run AI Evaluation",
                        on_click=FacilitatorState.trigger_evaluation_tab_ai_eval,
                        background="#027A48",
                        color="white",
                        size="2",
                        _hover={"background": "#05603A"},
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            max_width="500px",
            padding="1.8em",
            border_radius="14px",
        ),
        open=FacilitatorState.show_ai_eval_modal,
        on_open_change=FacilitatorState.set_show_ai_eval_modal,
    )


def evaluation_tab() -> rx.Component:
    """Evaluation tab interface matching reference screenshot exactly."""
    return rx.vstack(
        evaluation_test_header(),
        evaluation_candidate_selection_card(),
        evaluation_files_card(),
        rx.hstack(
            rx.box(evaluation_methods_card(), flex="1", margin_top="0"),
            rx.box(evaluation_ai_results_card(), flex="1", margin_top="0"),
            spacing="5",
            width="100%",
            align_items="stretch",
        ),
        candidate_response_modal(),
        manual_evaluation_modal(),
        answer_key_upload_modal(),
        ai_evaluation_trigger_modal(),
        spacing="4",
        width="100%",
        align_items="stretch",
    )



# ──────────────────────────────────────────────────────────────────────────────
# Results Tab — Performance Summary & AI Analytics
# ──────────────────────────────────────────────────────────────────────────────

def results_summary_card(
    icon_name: str,
    label: str,
    value: str,
    subtext: str,
    bg_color: str,
    icon_color: str,
    text_color: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon_name, size=24, color=icon_color),
                background=bg_color,
                padding="0.75em",
                border_radius="10px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(
                    label,
                    font_family=FONT_BODY,
                    size="1",
                    weight="bold",
                    color=COLORS["slate"],
                    letter_spacing="0.04em",
                ),
                rx.text(
                    value,
                    font_family=FONT_DISPLAY,
                    size="7",
                    weight="bold",
                    color=text_color,
                ),
                rx.text(
                    subtext,
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="0",
                align_items="start",
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.2em 1.5em",
        flex="1",
        min_width="220px",
    )


def results_dimension_tab_pill(tab_key: str, label: str) -> rx.Component:
    is_active = FacilitatorState.results_active_dimension_tab == tab_key
    return rx.box(
        rx.text(
            label,
            font_family=FONT_BODY,
            size="2",
            weight=rx.cond(is_active, "bold", "medium"),
            color=rx.cond(is_active, "white", "#475467"),
        ),
        background=rx.cond(is_active, "#4F46E5", "#F1F5F9"),
        padding="0.45em 1.1em",
        border_radius="8px",
        cursor="pointer",
        on_click=FacilitatorState.set_results_dimension_tab(tab_key),
        _hover={"background": rx.cond(is_active, "#4338CA", "#E2E8F0")},
        transition="all 0.15s ease",
    )


def results_vertical_bar_item(item: dict) -> rx.Component:
    """Renders a single vertical bar matching the reference image."""
    return rx.vstack(
        # Bar column container
        rx.box(
            # Pass mark dotted line background is at parent level
            # Top badge / percentage
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
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
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
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                    position="absolute",
                    bottom=f"calc({item['score']}% + 6px)",
                    left="50%",
                    transform="translateX(-50%)",
                    width="100%",
                    text_align="center",
                ),
            ),
            # The vertical bar itself
            rx.box(
                position="absolute",
                bottom="0",
                left="50%",
                transform="translateX(-50%)",
                width="64px",
                height=f"{item['score']}%",
                background=rx.cond(item["is_final"], "#4F46E5", "#818CF8"),
                border_radius="6px 6px 0 0",
                transition="height 0.3s ease",
            ),
            position="relative",
            width="80px",
            height="180px",
        ),
        # Label below bar
        rx.text(
            item["name"],
            font_family=FONT_BODY,
            size="2",
            weight="medium",
            color=COLORS["slate"],
            text_align="center",
            padding_top="0.4em",
        ),
        spacing="0",
        align_items="center",
    )


def results_vertical_bar_chart() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            # Y-Axis Label
            rx.box(
                rx.text(
                    "Performance (%)",
                    font_family=FONT_BODY,
                    size="1",
                    weight="medium",
                    color=COLORS["slate"],
                    transform="rotate(-90deg)",
                    white_space="nowrap",
                ),
                display="flex",
                align_items="center",
                justify_content="center",
                width="24px",
            ),
            # Y-Axis Ticks
            rx.vstack(
                rx.text("100%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                rx.text("75%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                rx.text("50%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                rx.text("25%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                rx.text("0%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                style={"justify_content": "space-between"},
                height="180px",
                align_items="end",
                padding_right="0.5em",
                flex_direction="column",
                display="flex",
            ),
            # Chart Canvas
            rx.box(
                # Horizontal Gridlines
                rx.box(position="absolute", left="0", right="0", top="0%", border_top="1px dashed #E2E8F0", z_index="1"),
                rx.box(position="absolute", left="0", right="0", top="25%", border_top="1px dashed #E2E8F0", z_index="1"),
                # Red 50% Pass Mark Dotted Line
                rx.box(position="absolute", left="0", right="0", top="50%", border_top="1.5px dashed #EF4444", z_index="2"),
                rx.box(
                    rx.text("Pass Mark", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                    rx.text("50%", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                    background="#FEF2F2",
                    border="1px solid #FECACA",
                    border_radius="4px",
                    padding="0.1em 0.35em",
                    position="absolute",
                    right="-68px",
                    top="calc(50% - 14px)",
                    z_index="3",
                ),
                rx.box(position="absolute", left="0", right="0", top="75%", border_top="1px dashed #E2E8F0", z_index="1"),
                rx.box(position="absolute", left="0", right="0", top="100%", border_top="1px solid #CBD5E1", z_index="1"),

                # Bars row
                rx.hstack(
                    rx.foreach(
                        FacilitatorState.results_tests_items,
                        lambda item: results_vertical_bar_item(item),
                    ),
                    style={"justify_content": "space-around"},
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
                margin_right="80px",
            ),
            spacing="1",
            align_items="center",
            width="100%",
        ),
        # X-Axis Title
        rx.text(
            "Assessment / Test",
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color=COLORS["slate"],
            text_align="center",
            width="100%",
            padding_top="0.6em",
        ),
        spacing="1",
        width="100%",
    )


def results_horizontal_dimension_row(item: dict) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(item["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
            rx.spacer(),
            rx.text(
                item["score"].to_string(), "%",
                font_family=FONT_BODY,
                size="2",
                weight="bold",
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
            # 50% Pass threshold line
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


def results_horizontal_bar_chart() -> rx.Component:
    return rx.vstack(
        # Guide Header
        rx.hstack(
            rx.text("Dimension / Competency", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
            rx.spacer(),
            rx.box(
                rx.text("50% Pass Mark", font_family=FONT_BODY, size="1", color="#DC2626", weight="bold"),
                padding_right="80px",
            ),
            rx.text("Score (%)", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
            width="100%",
            padding_bottom="0.4em",
            border_bottom="1px solid #F1F5F9",
        ),
        rx.vstack(
            rx.foreach(
                FacilitatorState.results_current_dimension_items,
                lambda item: results_horizontal_dimension_row(item),
            ),
            spacing="2",
            width="100%",
            padding_top="0.4em",
        ),
        spacing="1",
        width="100%",
    )


def results_key_insight_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("trending-up", size=16, color="#4F46E5"),
                rx.text(
                    "KEY INSIGHT",
                    font_family=FONT_BODY,
                    size="1",
                    weight="bold",
                    color="#64748B",
                    letter_spacing="0.05em",
                ),
                spacing="2",
                align_items="center",
                padding_bottom="1.2em",
            ),
            rx.text(
                "Performance improved by",
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.hstack(
                rx.text(
                    FacilitatorState.results_insight_diff_val.to_string(),
                    font_family=FONT_DISPLAY,
                    size="9",
                    weight="bold",
                    color="#059669",
                    line_height="1",
                ),
                rx.text(
                    "percentage points",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="baseline",
                margin_y="0.3em",
            ),
            rx.text(
                "from ",
                FacilitatorState.results_insight_start_val,
                " to ",
                FacilitatorState.results_insight_end_val,
                ".",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                weight="bold",
            ),
            spacing="1",
            align_items="start",
            width="100%",
        ),
        background="#F8FAFC",
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.6em 1.4em",
        width="32%",
        min_width="240px",
    )


def results_performance_analysis_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Top Header Row
            rx.hstack(
                rx.hstack(
                    rx.icon("bar-chart-2", size=20, color=COLORS["primary"]),
                    rx.text(
                        "Performance Analysis",
                        font_family=FONT_BODY,
                        size="4",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.icon("circle-help", size=14, color=COLORS["slate"]),
                    rx.text(
                        "All scores are in percentage (%)",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="1",
                    align_items="center",
                ),
                width="100%",
                align_items="center",
                padding_bottom="1em",
            ),

            # Dimension Tab Pills
            rx.hstack(
                results_dimension_tab_pill("overall", "Overall"),
                results_dimension_tab_pill("co", "CO"),
                results_dimension_tab_pill("lo", "LO"),
                results_dimension_tab_pill("knowledge_type", "Knowledge Type"),
                results_dimension_tab_pill("domain", "Domain"),
                results_dimension_tab_pill("rbt_level", "RBT Level"),
                spacing="2",
                width="100%",
                padding_bottom="1.4em",
                wrap="wrap",
            ),

            # Main Chart & Key Insight
            rx.hstack(
                rx.vstack(
                    rx.text(
                        FacilitatorState.results_chart_title,
                        font_family=FONT_BODY,
                        size="1",
                        weight="bold",
                        color=COLORS["ink"],
                        letter_spacing="0.03em",
                        padding_bottom="1em",
                    ),
                    rx.cond(
                        FacilitatorState.results_active_dimension_tab == "overall",
                        results_vertical_bar_chart(),
                        results_horizontal_bar_chart(),
                    ),
                    spacing="0",
                    width="100%",
                    align_items="stretch",
                    flex="1",
                ),
                results_key_insight_card(),
                spacing="5",
                width="100%",
                align_items="start",
            ),

            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.6em",
        width="100%",
    )


def results_candidate_summary_table_row(cand: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.badge(
                f"#{cand['rank']}",
                color_scheme="indigo",
                variant="solid",
                size="1",
            ),
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(cand["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                rx.text(cand["emp_id"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(
                    cand["overall_score"].to_string(), "%",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                    min_width="42px",
                ),
                rx.box(
                    rx.box(
                        width=f"{cand['overall_score']}%",
                        height="100%",
                        background="#4F46E5",
                        border_radius="4px",
                    ),
                    width="96px",
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
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                    min_width="42px",
                ),
                rx.box(
                    rx.box(
                        width=f"{cand['final_test_score']}%",
                        height="100%",
                        background="#059669",
                        border_radius="4px",
                    ),
                    width="96px",
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


def results_candidate_summary_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("user", size=18, color=COLORS["primary"]),
                rx.text(
                    "Candidate Summary",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                padding_bottom="0.8em",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            rx.text("Rank", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                            width="65px",
                        ),
                        rx.table.column_header_cell(
                            rx.text("Candidate", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Overall Score", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Final Test Score", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Result", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                            width="90px",
                        ),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        FacilitatorState.results_candidate_summary_rows,
                        lambda cand: results_candidate_summary_table_row(cand),
                    ),
                ),
                width="100%",
            ),
            rx.center(
                rx.text(
                    "View All Candidates →",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["primary"],
                    cursor="pointer",
                    padding_top="1em",
                    _hover={"text_decoration": "underline"},
                ),
                width="100%",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.5em",
        width="65%",
    )


def results_how_to_read_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "How to Read This Dashboard",
                font_family=FONT_BODY,
                size="3",
                weight="bold",
                color=COLORS["ink"],
                padding_bottom="0.8em",
            ),
            # 6 Guidelines with distinct colored icons matching reference image
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("bar-chart-2", size=15, color="#4F46E5"),
                        background="#EEF2FF",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("Overall: "),
                        "Shows performance across all assessments/tests.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                rx.hstack(
                    rx.box(
                        rx.icon("target", size=15, color="#059669"),
                        background="#ECFDF3",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("CO: "),
                        "Performance against Course Outcomes.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                rx.hstack(
                    rx.box(
                        rx.icon("graduation-cap", size=15, color="#D97706"),
                        background="#FFFAEB",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("LO: "),
                        "Performance against Learning Outcomes.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                rx.hstack(
                    rx.box(
                        rx.icon("book-open", size=15, color="#2563EB"),
                        background="#EFF8FF",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("Knowledge Type: "),
                        "Conceptual, Procedural and Application based performance.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                rx.hstack(
                    rx.box(
                        rx.icon("building-2", size=15, color="#0D9488"),
                        background="#F0FDFA",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("Domain: "),
                        "Performance across knowledge domains.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                rx.hstack(
                    rx.box(
                        rx.icon("brain", size=15, color="#6366F1"),
                        background="#EEF2FF",
                        padding="0.4em",
                        border_radius="6px",
                    ),
                    rx.text(
                        rx.text.strong("RBT Level: "),
                        "Performance based on Revised Bloom's Taxonomy.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="start",
                ),
                spacing="3",
                width="100%",
            ),
            rx.text(
                "Pass Mark is 50%. Scores at or above 50% are considered Passed.",
                font_family=FONT_BODY,
                size="1",
                color=COLORS["slate"],
                padding_top="1em",
                border_top=f"1px solid {COLORS['line']}",
                width="100%",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="14px",
        padding="1.5em",
        width="35%",
    )


def results_tab() -> rx.Component:
    """Redesigned Results Analytics tab matching reference visual design."""
    return rx.vstack(
        # ── Header ──────────────────────────────────────────────────────
        rx.hstack(
            rx.vstack(
                rx.text(
                    "AI Evaluation Results & Analytics",
                    font_family=FONT_DISPLAY,
                    size="6",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.text(
                    "Track candidate performance across assessments, learning outcomes and competency dimensions.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                align_items="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14),
                "Download AI Report (CSV)",
                on_click=FacilitatorState.mock_download_results,
                size="2",
                variant="outline",
                color=COLORS["primary"],
                border=f"1px solid {COLORS['primary']}",
                font_family=FONT_BODY,
                _hover={"background": COLORS["primary_soft"]},
            ),
            width="100%",
            align_items="center",
            padding_bottom="1.5em",
        ),

        # ── 1. Summary Cards (Row of 3) ─────────────────────────────────
        rx.hstack(
            results_summary_card(
                "trending-up",
                "OVERALL SCORE",
                FacilitatorState.results_overall_score_val + "%",
                "Overall Assessment Score",
                "#EEF2FF",
                "#4F46E5",
                "#2563EB",
            ),
            results_summary_card(
                "star",
                "FINAL TEST SCORE",
                FacilitatorState.results_final_test_score_val + "%",
                "Final Test Score",
                "#ECFDF3",
                "#059669",
                "#059669",
            ),
            results_summary_card(
                "shield-check",
                "PASSING RATE",
                FacilitatorState.results_passing_rate_val,
                FacilitatorState.results_passing_count_val,
                "#EFF6FF",
                "#2563EB",
                "#2563EB",
            ),
            spacing="3",
            width="100%",
            wrap="wrap",
        ),

        # ── 2. Candidate Filter ─────────────────────────────────────────
        rx.hstack(
            rx.text(
                "View Performance For",
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["ink"],
            ),
            rx.hstack(
                rx.icon("users", size=15, color=COLORS["slate"]),
                rx.select(
                    FacilitatorState.results_candidate_options,
                    value=FacilitatorState.results_selected_candidate,
                    on_change=FacilitatorState.set_results_selected_candidate,
                    size="2",
                    variant="surface",
                    min_width="190px",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="8px",
                padding="0.1em 0.5em",
                align_items="center",
            ),
            spacing="3",
            align_items="center",
            padding_y="1.2em",
        ),

        # ── 3. Main Performance Analysis Card ───────────────────────────
        results_performance_analysis_card(),

        # ── 4. Candidate Summary & How to Read Dashboard ───────────────
        rx.hstack(
            results_candidate_summary_card(),
            results_how_to_read_card(),
            spacing="4",
            width="100%",
            align_items="stretch",
            margin_top="1.5em",
        ),

        spacing="0",
        width="100%",
        align_items="stretch",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Question Paper Excel Spreadsheet Viewer Dialog
# ──────────────────────────────────────────────────────────────────────────────

def qp_preview_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Excel Ribbon Header
                rx.hstack(
                    rx.box(
                        rx.icon("file-spreadsheet", size=22, color="white"),
                        background="#107C41",
                        padding="0.45em",
                        border_radius="6px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.text(
                                FacilitatorState.viewing_qp_filename,
                                font_family=FONT_BODY,
                                size="3",
                                weight="bold",
                                color="#0F172A",
                            ),
                            rx.badge("Microsoft Excel (.xlsx)", color_scheme="green", variant="soft", size="1"),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.text(
                            "Workbook: ", FacilitatorState.viewing_qp_assessment_name, "  •  Test Stage: ", FacilitatorState.viewing_qp_test_name,
                            font_family=FONT_BODY,
                            size="1",
                            color="#64748B",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.badge(
                        FacilitatorState.excel_total_rows_count.to_string(), " Questions / Rows",
                        color_scheme="indigo",
                        variant="soft",
                        size="2",
                    ),
                    rx.badge(
                        FacilitatorState.excel_total_cols_count.to_string(), " Columns",
                        color_scheme="gray",
                        variant="soft",
                        size="2",
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.8em",
                    border_bottom="1px solid #E2E8F0",
                ),

                # Excel Formula Bar
                rx.hstack(
                    rx.box(
                        rx.text("fx", font_family="serif", font_style="italic", weight="bold", size="2", color="#64748B"),
                        background="#F1F5F9",
                        padding="0.2em 0.6em",
                        border_radius="4px",
                        border="1px solid #CBD5E1",
                    ),
                    rx.box(
                        rx.text(
                            "=", FacilitatorState.viewing_qp_filename, "!", FacilitatorState.excel_sheet_name, "$A$1:$I$", (FacilitatorState.excel_total_rows_count + 1).to_string(),
                            font_family="monospace",
                            size="1",
                            color="#334155",
                        ),
                        background="#FFFFFF",
                        border="1px solid #CBD5E1",
                        border_radius="4px",
                        padding="0.3em 0.8em",
                        flex="1",
                    ),
                    width="100%",
                    align_items="center",
                    padding="0.4em 0",
                ),

                # Spreadsheet Grid View
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("#", font_family="monospace", size="1", color="#64748B", weight="bold", text_align="center"),
                                    background="#E2E8F0",
                                    border_right="2px solid #CBD5E1",
                                    border_bottom="2px solid #CBD5E1",
                                    padding="0.5em 0.8em",
                                    width="40px",
                                    min_width="40px",
                                ),
                                rx.foreach(
                                    FacilitatorState.excel_headers,
                                    lambda h: rx.table.column_header_cell(
                                        rx.text(h, font_family=FONT_BODY, size="2", color="#0F172A", weight="bold"),
                                        background="#F1F5F9",
                                        border_right="1px solid #E2E8F0",
                                        border_bottom="2px solid #CBD5E1",
                                        padding="0.6em 0.9em",
                                        white_space="nowrap",
                                    ),
                                ),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                FacilitatorState.excel_rows,
                                lambda r, idx: rx.table.row(
                                    rx.table.cell(
                                        rx.text(
                                            (idx + 1).to_string(),
                                            font_family="monospace",
                                            size="1",
                                            color="#64748B",
                                            weight="bold",
                                            text_align="center",
                                        ),
                                        background="#F8FAFC",
                                        border_right="2px solid #CBD5E1",
                                        border_bottom="1px solid #E2E8F0",
                                        padding="0.6em 0.8em",
                                        width="40px",
                                        min_width="40px",
                                    ),
                                    rx.foreach(
                                        r,
                                        lambda val: rx.table.cell(
                                            rx.text(val, font_family=FONT_BODY, size="2", color="#1E293B"),
                                            border_right="1px solid #E2E8F0",
                                            border_bottom="1px solid #E2E8F0",
                                            padding="0.6em 0.9em",
                                            white_space="normal",
                                            min_width="120px",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    border="1px solid #CBD5E1",
                    border_radius="6px",
                    overflow="auto",
                    max_height="380px",
                    width="100%",
                    background="#FFFFFF",
                ),

                # Excel Bottom Sheet Tab Bar
                rx.hstack(
                    rx.box(
                        rx.hstack(
                            rx.icon("sheet", size=13, color="#107C41"),
                            rx.text(FacilitatorState.excel_sheet_name, font_family=FONT_BODY, size="1", weight="bold", color="#107C41"),
                            spacing="1",
                            align_items="center",
                        ),
                        background="#FFFFFF",
                        border_top="2px solid #107C41",
                        border_left="1px solid #CBD5E1",
                        border_right="1px solid #CBD5E1",
                        border_bottom="none",
                        padding="0.4em 1em",
                        border_radius="4px 4px 0 0",
                    ),
                    rx.spacer(),
                    rx.text("Excel Spreadsheet View  •  Ready", font_family=FONT_BODY, size="1", color="#64748B"),
                    width="100%",
                    align_items="center",
                    background="#F1F5F9",
                    padding="0.3em 0.8em 0 0.8em",
                    border_radius="0 0 6px 6px",
                    border="1px solid #CBD5E1",
                ),

                spacing="2",
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "Close Excel View",
                        variant="solid",
                        background="#107C41",
                        color="white",
                        font_family=FONT_BODY,
                        _hover={"background": "#0B5A2F"},
                    )
                ),
                padding_top="1.2em",
                width="100%",
            ),
            style={"maxWidth": "920px", "width": "90vw"},
        ),
        open=FacilitatorState.show_qp_preview_dialog,
        on_open_change=FacilitatorState.set_show_qp_preview_dialog,
    )


def add_new_test_dialog() -> rx.Component:
    is_formative = FacilitatorState.new_test_type == "Formative"
    is_summative = FacilitatorState.new_test_type == "Summative"

    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # ── Header ──────────────────────────────────────────────
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "Add New Test",
                            font_family=FONT_DISPLAY,
                            size="5",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "Create a new test for the assessment \"",
                            FacilitatorState.selected_assessment_name,
                            "\".",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        spacing="1",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=18),
                            size="2",
                            variant="ghost",
                            color_scheme="gray",
                            cursor="pointer",
                            on_click=FacilitatorState.close_add_test_modal,
                        ),
                    ),
                    width="100%",
                    align_items="start",
                    padding_bottom="0.5em",
                ),

                # ── Test Type Selection ─────────────────────────────────
                rx.vstack(
                    rx.hstack(
                        rx.text("Test Type", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        rx.text("*", font_family=FONT_BODY, size="2", weight="bold", color="#EF4444"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.hstack(
                        # Formative Option Card
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.cond(
                                        is_formative,
                                        rx.box(
                                            rx.box(width="8px", height="8px", border_radius="50%", background=COLORS["primary"]),
                                            width="18px",
                                            height="18px",
                                            border_radius="50%",
                                            border=f"2px solid {COLORS['primary']}",
                                            display="flex",
                                            align_items="center",
                                            justify_content="center",
                                        ),
                                        rx.box(
                                            width="18px",
                                            height="18px",
                                            border_radius="50%",
                                            border=f"2px solid {COLORS['line']}",
                                        ),
                                    ),
                                    flex_shrink=0,
                                ),
                                rx.box(
                                    rx.icon("file-text", size=18, color=COLORS["primary"]),
                                    background="#EDE9FE",
                                    padding="0.45em",
                                    border_radius="8px",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                    flex_shrink=0,
                                ),
                                rx.vstack(
                                    rx.text("Formative", font_family=FONT_BODY, size="2", weight="bold", color=rx.cond(is_formative, COLORS["primary"], COLORS["ink"])),
                                    rx.text("Ongoing assessment during the learning process.", font_family=FONT_BODY, size="1", color=COLORS["slate"], line_height="1.2"),
                                    spacing="0",
                                    align_items="start",
                                ),
                                spacing="3",
                                align_items="center",
                            ),
                            padding="0.85em 1em",
                            border_radius="12px",
                            border=rx.cond(is_formative, f"2px solid {COLORS['primary']}", f"1px solid {COLORS['line']}"),
                            background=rx.cond(is_formative, "#FAF5FF", "#FFFFFF"),
                            cursor="pointer",
                            flex="1",
                            on_click=FacilitatorState.set_new_test_type("Formative"),
                            transition="all 0.15s ease",
                        ),

                        # Summative Option Card
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.cond(
                                        is_summative,
                                        rx.box(
                                            rx.box(width="8px", height="8px", border_radius="50%", background=COLORS["primary"]),
                                            width="18px",
                                            height="18px",
                                            border_radius="50%",
                                            border=f"2px solid {COLORS['primary']}",
                                            display="flex",
                                            align_items="center",
                                            justify_content="center",
                                        ),
                                        rx.box(
                                            width="18px",
                                            height="18px",
                                            border_radius="50%",
                                            border=f"2px solid {COLORS['line']}",
                                        ),
                                    ),
                                    flex_shrink=0,
                                ),
                                rx.box(
                                    rx.icon("award", size=18, color="#D97706"),
                                    background="#FEF3C7",
                                    padding="0.45em",
                                    border_radius="8px",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                    flex_shrink=0,
                                ),
                                rx.vstack(
                                    rx.text("Summative", font_family=FONT_BODY, size="2", weight="bold", color=rx.cond(is_summative, COLORS["primary"], COLORS["ink"])),
                                    rx.text("Final assessment to measure overall learning.", font_family=FONT_BODY, size="1", color=COLORS["slate"], line_height="1.2"),
                                    spacing="0",
                                    align_items="start",
                                ),
                                spacing="3",
                                align_items="center",
                            ),
                            padding="0.85em 1em",
                            border_radius="12px",
                            border=rx.cond(is_summative, f"2px solid {COLORS['primary']}", f"1px solid {COLORS['line']}"),
                            background=rx.cond(is_summative, "#FAF5FF", "#FFFFFF"),
                            cursor="pointer",
                            flex="1",
                            on_click=FacilitatorState.set_new_test_type("Summative"),
                            transition="all 0.15s ease",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    align_items="start",
                ),

                # ── Test Name ───────────────────────────────────────────
                rx.vstack(
                    rx.hstack(
                        rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        rx.text("*", font_family=FONT_BODY, size="2", weight="bold", color="#EF4444"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.input(
                        value=FacilitatorState.new_test_name,
                        on_change=FacilitatorState.set_new_test_name,
                        placeholder="e.g. Formative 4",
                        width="100%",
                        border_radius="8px",
                        border=f"1px solid {COLORS['line']}",
                        font_family=FONT_BODY,
                        size="2",
                    ),
                    rx.text(
                        "You can edit the test name if needed.",
                        font_family=FONT_BODY,
                        size="1",
                        color=COLORS["slate"],
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),

                # ── Test Date ───────────────────────────────────────────
                rx.vstack(
                    rx.hstack(
                        rx.text("Test Date", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        rx.text("*", font_family=FONT_BODY, size="2", weight="bold", color="#EF4444"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.input(
                        rx.input.slot(
                            rx.icon("calendar", size=16, color=COLORS["slate"]),
                        ),
                        type="date",
                        value=FacilitatorState.new_test_date,
                        on_change=FacilitatorState.set_new_test_date,
                        width="100%",
                        size="2",
                        font_family=FONT_BODY,
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),

                # ── Description (Optional) ──────────────────────────────
                rx.vstack(
                    rx.text("Description (Optional)", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    rx.text_area(
                        value=FacilitatorState.new_test_description,
                        on_change=FacilitatorState.set_new_test_description,
                        placeholder="Enter a brief description about this test...",
                        max_length=200,
                        rows="3",
                        width="100%",
                        resize="none",
                        border_radius="8px",
                        border=f"1px solid {COLORS['line']}",
                        font_family=FONT_BODY,
                        size="2",
                    ),
                    rx.hstack(
                        rx.spacer(),
                        rx.text(
                            FacilitatorState.new_test_desc_counter,
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),

                # ── Info Callout ────────────────────────────────────────
                rx.box(
                    rx.hstack(
                        rx.icon("info", size=18, color=COLORS["primary"], flex_shrink=0),
                        rx.text(
                            "After creating the test, you can upload the Question Paper and Answer Key from the test management page.",
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["primary"],
                            weight="medium",
                            line_height="1.4",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#F5F3FF",
                    border="1px solid #E9D5FF",
                    border_radius="10px",
                    padding="0.8em 1em",
                    width="100%",
                ),

                # ── Actions ─────────────────────────────────────────────
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Cancel",
                        variant="outline",
                        color_scheme="gray",
                        on_click=FacilitatorState.close_add_test_modal,
                        font_family=FONT_BODY,
                        size="2",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        cursor="pointer",
                    ),
                    rx.button(
                        "Create Test",
                        on_click=FacilitatorState.create_new_test,
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        border_radius="8px",
                        _hover={"background": COLORS["primary_hover"]},
                        cursor="pointer",
                    ),
                    spacing="3",
                    width="100%",
                    align_items="center",
                    padding_top="0.5em",
                ),

                spacing="4",
                width="100%",
            ),
            style={"maxWidth": "540px", "width": "92vw", "padding": "1.8em", "borderRadius": "16px"},
        ),
        open=FacilitatorState.show_add_test_modal,
        on_open_change=FacilitatorState.set_show_add_test_modal,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Workspace page
# ──────────────────────────────────────────────────────────────────────────────

def assessment_workspace_page() -> rx.Component:
    content = rx.vstack(
        workspace_tab_bar(),
        rx.match(
            FacilitatorState.active_workspace_tab,
            ("question_paper", question_paper_tab()),
            ("evaluation", evaluation_tab()),
            ("results", results_tab()),
            # Fallback
            question_paper_tab(),
        ),
        qp_preview_dialog(),
        add_new_test_dialog(),
        spacing="0",
        width="100%",
        align_items="stretch",
    )

    return facilitator_shell(
        active="assessments",
        title=FacilitatorState.selected_assessment_name,
        subtitle="Assessment workspace",
        content=content,
    )