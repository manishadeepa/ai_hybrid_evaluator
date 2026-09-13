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
        workspace_tab("Weightage", "sliders-horizontal", "weightage",
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


def tests_tab_card(test: dict) -> rx.Component:
    """Reference-image style full-width test card with QP status and actions."""
    t_name = test["name"]
    t_date = test["date"]
    is_final = test["is_final"]
    has_file = test["has_qp"]

    return rx.box(
        rx.hstack(
            # Left: Icon box
            rx.box(
                rx.icon("file-text", size=22, color="#7C3AED"),
                background="#F5F3FF",
                padding="0.85em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Center: Name, type badge, date, QP status
            rx.vstack(
                rx.hstack(
                    rx.text(
                        t_name,
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge(
                        rx.cond(is_final, "Summative", "Formative"),
                        color_scheme=rx.cond(is_final, "purple", "blue"),
                        variant="soft",
                        size="1",
                        border_radius="12px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.hstack(
                    rx.icon("calendar", size=13, color=COLORS["slate"]),
                    rx.text(
                        "Test Date: ",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    rx.text(
                        rx.cond(t_date != "", t_date, "Not scheduled"),
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="1",
                    align_items="center",
                ),
                rx.cond(
                    has_file,
                    rx.hstack(
                        rx.icon("circle-check", size=14, color="#10B981"),
                        rx.text(
                            "Question Paper Uploaded",
                            font_family=FONT_BODY,
                            size="2",
                            color="#047857",
                            weight="medium",
                        ),
                        spacing="1",
                        align_items="center",
                        background="#ECFDF5",
                        border="1px solid #A7F3D0",
                        border_radius="20px",
                        padding="0.2em 0.8em",
                    ),
                    rx.hstack(
                        rx.icon("clock", size=14, color="#64748B"),
                        rx.text(
                            "No Question Paper",
                            font_family=FONT_BODY,
                            size="2",
                            color="#64748B",
                            weight="medium",
                        ),
                        spacing="1",
                        align_items="center",
                        background="#F8FAFC",
                        border="1px solid #E2E8F0",
                        border_radius="20px",
                        padding="0.2em 0.8em",
                    ),
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            # Vertical divider
            rx.box(
                width="1px",
                height="54px",
                background="#F1F5F9",
                margin_x="0.5em",
                flex_shrink=0,
            ),
            # Right: Action buttons + 3-dot menu
            rx.hstack(
                # View File (only when QP uploaded)
                rx.cond(
                    has_file,
                    rx.button(
                        rx.icon("eye", size=14),
                        "View File",
                        on_click=FacilitatorState.open_qp_preview(t_name, FacilitatorState.selected_assessment_name),
                        size="2",
                        variant="outline",
                        color_scheme="gray",
                        color="#1E293B",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        cursor="pointer",
                    ),
                ),
                # Replace File / Upload File
                rx.cond(
                    has_file,
                    rx.button(
                        rx.icon("refresh-cw", size=14),
                        "Replace File",
                        on_click=FacilitatorState.start_replacing_qp(t_name),
                        size="2",
                        background="#4F46E5",
                        color="white",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        _hover={"background": "#4338CA"},
                        cursor="pointer",
                    ),
                    rx.button(
                        rx.icon("upload", size=14),
                        "Upload File",
                        on_click=FacilitatorState.start_replacing_qp(t_name),
                        size="2",
                        variant="outline",
                        color_scheme="indigo",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        cursor="pointer",
                    ),
                ),
                # 3-dot menu
                rx.menu.root(
                    rx.menu.trigger(
                        rx.icon_button(
                            rx.icon("ellipsis-vertical", size=14),
                            variant="outline",
                            color_scheme="gray",
                            size="2",
                            border_radius="8px",
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
                flex_shrink=0,
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="1.2em 1.4em",
        border_radius="12px",
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        width="100%",
        _hover={"border_color": "#CBD5E1", "background": "#FAFAFC"},
        transition="all 0.15s ease",
    )


def tests_tab() -> rx.Component:
    """Tests tab — full-width card list matching the reference image."""
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

    cards_view = rx.vstack(
        # Page header with + Add Test button
        rx.hstack(
            rx.vstack(
                rx.text(
                    "Tests",
                    font_family=FONT_DISPLAY,
                    size="6",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.text(
                    "Create and manage tests for this assessment. Upload or replace question papers.",
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
            align_items="center",
            padding_bottom="1.2em",
        ),
        # Test cards list
        rx.vstack(
            rx.foreach(test_items, tests_tab_card),
            spacing="3",
            width="100%",
        ),
        # Supported formats banner (matching reference design)
        rx.box(
            rx.hstack(
                rx.icon("info", size=20, color="#6366F1"),
                rx.vstack(
                    rx.text(
                        "Supported Formats",
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        ".xlsx, .xls, .pdf, .docx, .doc, .csv  •  Max size: 10MB",
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
            padding="1.1em 1.4em",
            background="#F8FAFC",
            border="1px solid #E2E8F0",
            border_radius="12px",
            width="100%",
            margin_top="1em",
        ),
        spacing="0",
        width="100%",
        align_items="stretch",
    )

    return rx.cond(
        test_items.length() > 0,
        cards_view,
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Tests",
                        font_family=FONT_DISPLAY,
                        size="6",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Create and manage tests for this assessment. Upload or replace question papers.",
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
                align_items="center",
                padding_bottom="1.2em",
            ),
            empty_state,
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
    )


def question_paper_tab() -> rx.Component:
    """Backward compatibility alias for tests_tab."""
    return tests_tab()


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
                rx.cond(
                    FacilitatorState.has_eval_qp,
                    rx.badge("Available", color_scheme="green", variant="soft", size="1"),
                    rx.badge("Not Uploaded", color_scheme="gray", variant="soft", size="1"),
                ),
                rx.button(
                    rx.icon("eye", size=13),
                    "View File",
                    on_click=FacilitatorState.open_qp_preview(FacilitatorState.selected_test_name, FacilitatorState.selected_assessment_name),
                    size="1",
                    variant="soft",
                    color_scheme="indigo",
                    font_family=FONT_BODY,
                    disabled=~FacilitatorState.has_eval_qp,
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
                rx.hstack(
                    rx.box(
                        rx.icon("bar-chart-2", size=18, color="#7C3AED"),
                        background="#F4F3FF",
                        border_radius="6px",
                        padding="0.35em",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text(
                        "AI Evaluation Results",
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="center",
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
                padding_bottom="0.8em",
            ),

            # Status Alert Banner
            rx.cond(
                FacilitatorState.has_ai_evaluated_current_candidate,
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=16, color="#027A48"),
                        rx.text(
                            "AI evaluation completed successfully",
                            font_family=FONT_BODY,
                            size="1",
                            color="#027A48",
                            weight="medium",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#ECFDF3",
                    border="1px solid #A6F4C5",
                    border_radius="8px",
                    padding="0.6em 0.9em",
                    width="100%",
                    margin_bottom="0.8em",
                ),
            ),

            # 3 Score Metric Cards matching Reference UI
            rx.hstack(
                # Card 1: Marks Obtained
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-text", size=18, color="#7C3AED"),
                            background="#F4F3FF",
                            border_radius="8px",
                            padding="0.65em",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text("Marks Obtained", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                            rx.text(
                                FacilitatorState.current_candidate_ai_score_display,
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    padding="0.85em 1em",
                    flex="1",
                ),
                # Card 2: Normalized Score
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("shield-check", size=18, color="#2563EB"),
                            background="#EFF8FF",
                            border_radius="8px",
                            padding="0.65em",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text("Normalized Score", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                            rx.text(
                                FacilitatorState.current_candidate_ai_percentage_display,
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text("(Out of 100)", font_family=FONT_BODY, size="1", color=COLORS["placeholder"]),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    padding="0.85em 1em",
                    flex="1",
                ),
                # Card 3: Status
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon(
                                rx.cond(
                                    FacilitatorState.has_ai_evaluated_current_candidate,
                                    "circle-check",
                                    "clock",
                                ),
                                size=18,
                                color=rx.cond(
                                    FacilitatorState.has_ai_evaluated_current_candidate,
                                    "#027A48",
                                    COLORS["slate"],
                                ),
                            ),
                            background=rx.cond(
                                FacilitatorState.has_ai_evaluated_current_candidate,
                                "#ECFDF3",
                                "#F2F4F7",
                            ),
                            border_radius="8px",
                            padding="0.65em",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.text("Status", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                            rx.text(
                                rx.cond(
                                    FacilitatorState.has_ai_evaluated_current_candidate,
                                    "Completed",
                                    "Pending",
                                ),
                                font_family=FONT_DISPLAY,
                                size="4",
                                weight="bold",
                                color=rx.cond(
                                    FacilitatorState.has_ai_evaluated_current_candidate,
                                    "#027A48",
                                    COLORS["slate"],
                                ),
                            ),
                            rx.cond(
                                FacilitatorState.has_ai_evaluated_current_candidate,
                                rx.text(
                                    FacilitatorState.current_candidate_ai_eval_date,
                                    font_family=FONT_BODY,
                                    size="1",
                                    color=COLORS["placeholder"],
                                ),
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    padding="0.85em 1em",
                    flex="1",
                ),
                spacing="3",
                width="100%",
                margin_bottom="1em",
            ),

            # Question-wise Results Heading
            rx.text(
                "Question-wise Results",
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
                padding_top="0.4em",
                padding_bottom="0.5em",
            ),

            # Question-wise Breakdown Table
            rx.cond(
                FacilitatorState.has_ai_evaluated_current_candidate,
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("Q No.", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="80px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Marks Obtained", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="120px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Max Marks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="90px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Score (Out of 100)", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                    width="140px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Remarks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
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
                                        rx.text(q["score_pct"], font_family=FONT_BODY, size="1", weight="medium", color="#2563EB"),
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
                                rx.table.cell(rx.text(FacilitatorState.current_candidate_ai_percentage_display, font_family=FONT_BODY, size="1", weight="bold", color="#2563EB")),
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


def ai_eval_progress_modal() -> rx.Component:
    """Fullscreen overlay showing per-question AI evaluation progress."""
    total = FacilitatorState.eval_progress_questions.length()
    completed = FacilitatorState.eval_progress_current
    pct = rx.cond(
        total > 0,
        (completed * 100 // total),
        0,
    )

    def question_row(q: dict) -> rx.Component:
        is_completed = q["status"] == "completed"
        is_evaluating = q["status"] == "evaluating"
        return rx.hstack(
            # Number badge
            rx.box(
                rx.cond(
                    is_completed,
                    rx.icon("check", size=12, color="white"),
                    rx.cond(
                        is_evaluating,
                        rx.icon("loader", size=12, color="white"),
                        rx.text("·", color="#94A3B8", size="2", font_weight="700"),
                    ),
                ),
                width="24px",
                height="24px",
                border_radius="50%",
                display="flex",
                align_items="center",
                justify_content="center",
                background=rx.cond(
                    is_completed,
                    "#027A48",
                    rx.cond(is_evaluating, "#6C3FF4", "#E2E8F0"),
                ),
                flex_shrink="0",
            ),
            rx.text(
                q["label"],
                font_family=FONT_BODY,
                size="2",
                font_weight=rx.cond(is_evaluating, "600", "400"),
                color=rx.cond(
                    is_completed,
                    "#027A48",
                    rx.cond(is_evaluating, "#6C3FF4", "#64748B"),
                ),
            ),
            rx.spacer(),
            rx.cond(
                is_completed,
                rx.hstack(
                    rx.icon("circle-check", size=14, color="#027A48"),
                    rx.text("Completed", size="2", color="#027A48", font_family=FONT_BODY, font_weight="500"),
                    spacing="1",
                    align_items="center",
                ),
                rx.cond(
                    is_evaluating,
                    rx.hstack(
                        rx.spinner(size="1", color="#6C3FF4"),
                        rx.text("Evaluating...", size="2", color="#6C3FF4", font_family=FONT_BODY, font_weight="500"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.icon("clock", size=14, color="#94A3B8"),
                        rx.text("Pending", size="2", color="#94A3B8", font_family=FONT_BODY),
                        spacing="1",
                        align_items="center",
                    ),
                ),
            ),
            width="100%",
            padding="0.65em 0.9em",
            border_radius="8px",
            background=rx.cond(
                is_evaluating,
                "rgba(108,63,244,0.07)",
                rx.cond(is_completed, "rgba(2,122,72,0.05)", "transparent"),
            ),
            border=rx.cond(
                is_evaluating,
                "1px solid rgba(108,63,244,0.2)",
                rx.cond(is_completed, "1px solid rgba(2,122,72,0.15)", "1px solid #F1F5F9"),
            ),
            align_items="center",
            spacing="3",
        )

    return rx.cond(
        FacilitatorState.show_eval_progress_modal,
        rx.box(
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.box(
                            rx.icon("sparkles", size=18, color="#6C3FF4"),
                            background="#EDE9FE",
                            padding="0.5em",
                            border_radius="8px",
                            flex_shrink="0",
                        ),
                        rx.text(
                            "AI Evaluation in Progress",
                            font_family=FONT_DISPLAY,
                            size="4",
                            font_weight="700",
                            color="#1E293B",
                        ),
                        rx.spacer(),
                        rx.icon_button(
                            rx.icon("x", size=16),
                            on_click=FacilitatorState.close_eval_progress_modal,
                            size="2",
                            variant="ghost",
                            color="#64748B",
                            cursor="pointer",
                            _hover={"background": "#F1F5F9", "color": "#1E293B"},
                            border_radius="6px",
                        ),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),
                    # Description
                    rx.vstack(
                        rx.text(
                            "AI is evaluating the candidate response question by question.",
                            font_family=FONT_BODY,
                            size="2",
                            color="#475569",
                        ),
                        rx.text(
                            "Please do not close this window. This may take a few minutes.",
                            font_family=FONT_BODY,
                            size="2",
                            color="#94A3B8",
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    # Progress bar + text
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                rx.box(
                                    height="8px",
                                    border_radius="99px",
                                    background="linear-gradient(90deg, #6C3FF4, #9B6DFA)",
                                    width=pct.to_string() + "%",
                                    transition="width 0.5s ease",
                                ),
                                background="#EDE9FE",
                                border_radius="99px",
                                height="8px",
                                flex="1",
                                overflow="hidden",
                            ),
                            rx.text(
                                completed.to_string() + " of " + total.to_string() + " questions evaluated",
                                font_family=FONT_BODY,
                                size="1",
                                color="#64748B",
                                white_space="nowrap",
                            ),
                            rx.text(
                                pct.to_string() + "%",
                                font_family=FONT_BODY,
                                size="1",
                                font_weight="600",
                                color="#6C3FF4",
                                white_space="nowrap",
                            ),
                            spacing="3",
                            align_items="center",
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    # Question list
                    rx.vstack(
                        rx.foreach(
                            FacilitatorState.eval_progress_questions,
                            question_row,
                        ),
                        spacing="2",
                        width="100%",
                        max_height="320px",
                        overflow_y="auto",
                    ),
                    spacing="4",
                    width="100%",
                    padding="1.8em",
                ),
                background="white",
                border_radius="16px",
                box_shadow="0 24px 64px rgba(0,0,0,0.22)",
                max_width="520px",
                width="92vw",
            ),
            position="fixed",
            top="0",
            left="0",
            width="100vw",
            height="100vh",
            background="rgba(15,23,42,0.55)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="9999",
            backdrop_filter="blur(2px)",
        ),
        rx.fragment(),
    )


def evaluation_tab() -> rx.Component:
    """Evaluation tab interface matching reference screenshot exactly."""
    return rx.vstack(
        evaluation_test_header(),
        evaluation_candidate_selection_card(),
        evaluation_files_card(),
        evaluation_methods_card(),
        evaluation_ai_results_card(),
        candidate_response_modal(),
        manual_evaluation_modal(),
        answer_key_upload_modal(),
        ai_evaluation_trigger_modal(),
        ai_eval_progress_modal(),
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


def results_vertical_dimension_bar_item(item: dict) -> rx.Component:
    """Renders a single vertical bar for any dimension (CO, LO, KT, Domain, RBT, Tests)."""
    return rx.box(
        # Score percentage above bar
        rx.text(
            item["score"].to_string(), "%",
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color=COLORS["ink"],
            position="absolute",
            bottom=f"calc({item['score']}% + 4px)",
            left="50%",
            transform="translateX(-50%)",
            text_align="center",
            white_space="nowrap",
            z_index="4",
        ),
        # The vertical bar itself - anchored to bottom 0 of canvas
        rx.box(
            position="absolute",
            bottom="0",
            left="50%",
            transform="translateX(-50%)",
            width="60%",
            max_width="48px",
            min_width="14px",
            style={"height": item["score"].to_string() + "%"},
            background="#5B5BD6",
            border_radius="6px 6px 0 0",
            transition="height 0.3s ease",
            z_index="2",
        ),
        # Label (e.g. LO-1.1, CO-1.0) positioned directly beneath baseline
        rx.text(
            item["name"],
            font_family=FONT_BODY,
            size="1",
            weight="medium",
            color=COLORS["slate"],
            position="absolute",
            top="100%",
            left="50%",
            transform="translateX(-50%)",
            padding_top="6px",
            text_align="center",
            white_space="nowrap",
        ),
        position="relative",
        flex="1",
        min_width="0",
        max_width="72px",
        height="180px",
    )


def results_vertical_bar_chart() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            # Y-Axis Label
            rx.box(
                rx.text(
                    "Score (%)",
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
                width="28px",
                height="180px",
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
                rx.box(position="absolute", left="0", right="0", top="50%", border_top="1px dashed #E2E8F0", z_index="1"),
                rx.box(position="absolute", left="0", right="0", top="75%", border_top="1px dashed #E2E8F0", z_index="1"),
                rx.box(position="absolute", left="0", right="0", bottom="0", border_top="1px solid #CBD5E1", z_index="1"),

                # Dynamic Pass Mark Dotted Line
                rx.box(position="absolute", left="0", right="0", top=FacilitatorState.results_pass_line_top, border_top="1.5px dashed #EF4444", z_index="2"),
                rx.box(
                    rx.text("Pass Mark", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                    rx.text(FacilitatorState.results_pass_percentage_str, font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                    background="#FEF2F2",
                    border="1px solid #FECACA",
                    border_radius="4px",
                    padding="0.15em 0.45em",
                    position="absolute",
                    right="-74px",
                    top=FacilitatorState.results_pass_badge_top,
                    z_index="3",
                ),

                # Bars row
                rx.cond(
                    FacilitatorState.results_current_dimension_items.length() > 0,
                    rx.hstack(
                        rx.foreach(
                            FacilitatorState.results_current_dimension_items,
                            lambda item: results_vertical_dimension_bar_item(item),
                        ),
                        style={"justify_content": "space-evenly"},
                        align_items="end",
                        height="180px",
                        width="100%",
                        z_index="4",
                        position="relative",
                        padding_x="0.8em",
                    ),
                    rx.center(
                        rx.text(
                            "No mapped data available for this dimension in the selected test.",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["placeholder"],
                        ),
                        height="180px",
                        width="100%",
                    ),
                ),
                position="relative",
                height="180px",
                flex="1",
                min_width="0",
                border_left="1px solid #CBD5E1",
                border_bottom="1px solid #CBD5E1",
                margin_right="85px",
                margin_bottom="28px",
            ),
            spacing="1",
            align_items="start",
            width="100%",
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
            rx.cond(
                FacilitatorState.results_insight_start_val != "",
                rx.vstack(
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
                rx.vstack(
                    rx.text(
                        "Overall Score Attainment",
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.text(
                            FacilitatorState.results_overall_score_val,
                            font_family=FONT_DISPLAY,
                            size="9",
                            weight="bold",
                            color=rx.cond(FacilitatorState.results_is_passing, "#059669", "#DC2626"),
                            line_height="1",
                        ),
                        rx.text(
                            "%",
                            font_family=FONT_DISPLAY,
                            size="6",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        spacing="1",
                        align_items="baseline",
                        margin_y="0.3em",
                    ),
                    rx.text(
                        rx.cond(
                            FacilitatorState.results_selected_candidate == "All Candidates",
                            "Average across all evaluated candidates in this cohort.",
                            "Evaluated score for " + FacilitatorState.results_selected_candidate + ".",
                        ),
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),
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


def results_dimension_summary_card() -> rx.Component:
    summary = FacilitatorState.results_active_dimension_summary
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("layout-grid", size=14, color="white"),
                    background="#6366F1",
                    padding="0.35em",
                    border_radius="6px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(
                    "Summary",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                padding_bottom="0.8em",
            ),
            # 4-card horizontal stat row
            rx.grid(
                # Stat 1: Total items
                rx.vstack(
                    rx.text(summary["total_label"], font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(summary["total_val"], font_family=FONT_DISPLAY, size="7", weight="bold", color=COLORS["ink"]),
                    spacing="1",
                    align_items="center",
                    justify_content="center",
                    padding="1.1em 0.8em",
                    background="#F8FAFC",
                    border_radius="10px",
                    width="100%",
                ),
                # Stat 2: Above pass mark
                rx.vstack(
                    rx.text(summary["passing_label"], font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(summary["passing_val"], font_family=FONT_DISPLAY, size="7", weight="bold", color=COLORS["ink"]),
                    spacing="1",
                    align_items="center",
                    justify_content="center",
                    padding="1.1em 0.8em",
                    background="#F8FAFC",
                    border_radius="10px",
                    width="100%",
                ),
                # Stat 3: Average attainment
                rx.vstack(
                    rx.text(summary["avg_label"], font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(summary["avg_val"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#059669"),
                    spacing="1",
                    align_items="center",
                    justify_content="center",
                    padding="1.1em 0.8em",
                    background="#F8FAFC",
                    border_radius="10px",
                    width="100%",
                ),
                # Stat 4: Status badge
                rx.vstack(
                    rx.text("Status", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.badge(
                        summary["status"],
                        color_scheme=rx.cond(summary["is_passed"], "green", "red"),
                        variant="soft",
                        size="3",
                        padding="0.4em 1.2em",
                        border_radius="8px",
                    ),
                    spacing="2",
                    align_items="center",
                    justify_content="center",
                    padding="1.1em 0.8em",
                    background="#F8FAFC",
                    border_radius="10px",
                    width="100%",
                ),
                columns="4",
                spacing="3",
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
        margin_top="1.4em",
    )


def results_dimension_info_banner() -> rx.Component:
    summary = FacilitatorState.results_active_dimension_summary
    return rx.box(
        rx.hstack(
            rx.icon("info", size=16, color="#2563EB"),
            rx.text(
                summary["info_text"],
                font_family=FONT_BODY,
                size="2",
                color="#1E40AF",
            ),
            spacing="2",
            align_items="center",
        ),
        background="#EFF6FF",
        border="1px solid #BFDBFE",
        border_radius="8px",
        padding="0.75em 1em",
        width="100%",
        margin_top="1em",
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
                results_dimension_tab_pill("question_wise", "Question-wise"),
                spacing="2",
                width="100%",
                padding_bottom="1.4em",
                wrap="wrap",
            ),

            # Tab Content: switches according to selected tab
            rx.cond(
                FacilitatorState.results_active_dimension_tab == "question_wise",
                _results_question_analysis_section(),
                rx.vstack(
                    rx.text(
                        FacilitatorState.results_chart_title,
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                        letter_spacing="0.02em",
                        padding_bottom="1.2em",
                    ),
                    results_vertical_bar_chart(),
                    results_dimension_summary_card(),
                    results_dimension_info_banner(),
                    spacing="0",
                    width="100%",
                    align_items="stretch",
                ),
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


def results_candidate_test_breakdown_card() -> rx.Component:
    """Card displaying individual candidate test score breakdown with weightages."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("layers", size=18, color=COLORS["primary"]),
                rx.text(
                    "Test Score Breakdown & Weightage",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                rx.spacer(),
                rx.badge(
                    FacilitatorState.results_selected_candidate,
                    color_scheme="indigo",
                    variant="soft",
                    size="1",
                ),
                spacing="2",
                align_items="center",
                width="100%",
                padding_bottom="0.8em",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(rx.text("Test Name", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Type", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Marks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Normalized Score", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Weightage", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                        rx.table.column_header_cell(rx.text("Weighted Score", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"])),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        FacilitatorState.results_test_breakdown,
                        lambda row: rx.table.row(
                            rx.table.cell(rx.text(row["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                            rx.table.cell(
                                rx.badge(
                                    rx.cond(row["is_final"], "Summative", "Formative"),
                                    color_scheme=rx.cond(row["is_final"], "purple", "blue"),
                                    variant="soft",
                                    size="1",
                                )
                            ),
                            rx.table.cell(rx.text(row["marks_str"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                            rx.table.cell(
                                rx.box(
                                    rx.text(row["norm_score_str"], font_family=FONT_BODY, size="2", weight="bold", color="#059669"),
                                    background="#ECFDF3",
                                    border_radius="6px",
                                    padding="0.2em 0.6em",
                                    display="inline-flex",
                                )
                            ),
                            rx.table.cell(rx.text(row["weightage_str"], font_family=FONT_BODY, size="2", color=COLORS["ink"])),
                            rx.table.cell(
                                rx.box(
                                    rx.text(row["weighted_score_str"], font_family=FONT_BODY, size="2", weight="bold", color="#6C3FF4"),
                                    background="#F4F3FF",
                                    border_radius="6px",
                                    padding="0.2em 0.6em",
                                    display="inline-flex",
                                )
                            ),
                        ),
                    ),
                    # Overall total row
                    rx.table.row(
                        rx.table.cell(
                            rx.text("Overall Assessment Score", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                            col_span=3,
                        ),
                        rx.table.cell(
                            rx.text(FacilitatorState.results_overall_score_pct_str, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        ),
                        rx.table.cell(
                            rx.text(FacilitatorState.current_assessment_total_weightage_str, font_family=FONT_BODY, size="2", weight="bold", color="#6C3FF4"),
                        ),
                        rx.table.cell(
                            rx.text(FacilitatorState.results_overall_score_val, font_family=FONT_BODY, size="2", weight="bold", color="#6C3FF4"),
                        ),
                        background="#F9FAFB",
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


# ──────────────────────────────────────────────────────────────────────────────
# Weightage Tab Components
# ──────────────────────────────────────────────────────────────────────────────

def _weightage_row(test: dict) -> rx.Component:
    """A single test row in the weightage table."""
    return rx.table.row(
        # 1. Test Name
        rx.table.cell(
            rx.text(test["name"], font_family=FONT_BODY, size="2", color=COLORS["ink"], font_weight="500"),
        ),
        # 2. Test Type
        rx.table.cell(
            rx.badge(
                rx.cond(test["is_final"], "Summative", "Formative"),
                color_scheme=rx.cond(test["is_final"], "purple", "blue"),
                variant="soft",
                size="1",
            ),
        ),
        # 3. Test Date
        rx.table.cell(
            rx.text(
                rx.cond(test["date"] != "", test["date"], "—"),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
        ),
        # 4. Weightage (%)
        rx.table.cell(
            rx.hstack(
                rx.input(
                    placeholder="0",
                    default_value=test["weightage"],
                    on_change=lambda v: FacilitatorState.set_weightage_input(test["name"], v),
                    type="number",
                    min="0",
                    max="100",
                    width="72px",
                    font_family=FONT_BODY,
                    size="2",
                    text_align="right",
                    background="white",
                    border=f"1px solid {COLORS['line']}",
                    border_radius="6px",
                ),
                rx.text("%", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                spacing="1",
                align_items="center",
            ),
        ),
        # 5. Pass Percentage (%)
        rx.table.cell(
            rx.hstack(
                rx.input(
                    placeholder="50",
                    default_value=test["pass_percentage"],
                    on_change=lambda v: FacilitatorState.set_pass_percentage_input(test["name"], v),
                    type="number",
                    min="0",
                    max="100",
                    width="72px",
                    font_family=FONT_BODY,
                    size="2",
                    text_align="right",
                    background="white",
                    border=f"1px solid {COLORS['line']}",
                    border_radius="6px",
                ),
                rx.text("%", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                spacing="1",
                align_items="center",
            ),
        ),
        _hover={"background": "#F8F9FF"},
    )


def weightage_tab() -> rx.Component:
    """Test Weightage Configuration tab matching reference UI."""
    return rx.vstack(
        rx.box(
            rx.vstack(
                # ── Card header ─────────────────────────────────────────
                rx.hstack(
                    rx.box(
                        rx.icon("sliders-horizontal", size=18, color="#6C3FF4"),
                        background="#EDE9FE",
                        padding="0.5em",
                        border_radius="8px",
                        flex_shrink="0",
                    ),
                    rx.vstack(
                        rx.text(
                            "Test Weightage & Pass Percentage Configuration",
                            font_family=FONT_DISPLAY,
                            size="4",
                            font_weight="700",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "Set the weightage and pass percentage for each test in this assessment. Total weightage must equal 100%.",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        spacing="1",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                # ── Tests table ─────────────────────────────────────────
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Test Name", size="1", font_family=FONT_BODY, color=COLORS["slate"], font_weight="600"),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Test Type", size="1", font_family=FONT_BODY, color=COLORS["slate"], font_weight="600"),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Test Date", size="1", font_family=FONT_BODY, color=COLORS["slate"], font_weight="600"),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Weightage (%)", size="1", font_family=FONT_BODY, color=COLORS["slate"], font_weight="600"),
                            ),
                            rx.table.column_header_cell(
                                rx.text("Pass Percentage (%)", size="1", font_family=FONT_BODY, color=COLORS["slate"], font_weight="600"),
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(FacilitatorState.current_assessment_weightage_items, _weightage_row),
                        # Total row
                        rx.table.row(
                            rx.table.cell(
                                rx.text("Total Weightage", font_family=FONT_BODY, size="2", font_weight="700", color=COLORS["ink"]),
                                col_span=3,
                            ),
                            rx.table.cell(
                                rx.text(
                                    FacilitatorState.current_assessment_total_weightage_str,
                                    font_family=FONT_BODY,
                                    size="2",
                                    font_weight="800",
                                    color="#6C3FF4",
                                ),
                            ),
                            rx.table.cell(
                                rx.text("—", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                            ),
                            background="#F9FAFB",
                        ),
                    ),
                    width="100%",
                    variant="surface",
                    size="2",
                ),
                # ── Info banner ─────────────────────────────────────────
                rx.hstack(
                    rx.icon("info", size=16, color="#6C3FF4"),
                    rx.vstack(
                        rx.text(
                            "Total weightage must be exactly 100% to proceed.",
                            font_family=FONT_BODY,
                            size="2",
                            color="#344054",
                            weight="medium",
                        ),
                        rx.text(
                            "Tests that are not yet evaluated will be included in the calculation once evaluation is completed.",
                            font_family=FONT_BODY,
                            size="1",
                            color="#667085",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="2",
                    align_items="start",
                    padding="0.8em 1em",
                    background="#F8F9FC",
                    border="1px solid #E4E7EC",
                    border_radius="8px",
                    width="100%",
                ),
                # ── Save button ─────────────────────────────────────────
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.icon("bookmark", size=14),
                        "Save Weightage & Pass %",
                        on_click=FacilitatorState.save_weightage,
                        background="#6C3FF4",
                        color="white",
                        size="2",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        _hover={"background": "#5B35CC"},
                        cursor="pointer",
                    ),
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            background="white",
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.5em",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )



# ──────────────────────────────────────────────────────────────────────────────
# Reports Tab Components (Matching Reference Design)
# ──────────────────────────────────────────────────────────────────────────────

def reports_header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(
                "Reports",
                font_family=FONT_DISPLAY,
                size="6",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "Generate and view assessment reports for all tests. Download individual test reports or the overall assessment report.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            spacing="0",
            align_items="start",
        ),
        rx.spacer(),
        # Top-right Assessment info box
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=20, color="#2563EB"),
                    background="#EFF6FF",
                    padding="0.6em",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink=0,
                ),
                rx.vstack(
                    rx.text("Assessment", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(
                        rx.cond(
                            FacilitatorState.selected_assessment_name != "",
                            FacilitatorState.selected_assessment_name,
                            "Quality",
                        ),
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                rx.box(
                    width="1px",
                    height="32px",
                    background=COLORS["line"],
                    margin_x="0.6em",
                    flex_shrink=0,
                ),
                rx.vstack(
                    rx.text("Assessment Period", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(
                        "01 Sep 2026 - 31 Oct 2026",
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="2",
                align_items="center",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="0.6em 1.2em",
        ),
        width="100%",
        align_items="center",
        padding_bottom="0.8em",
    )


def reports_pass_percentage_card() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: Icon & Description
            rx.hstack(
                rx.box(
                    rx.icon("target", size=22, color="#6366F1"),
                    background="#EDE9FE",
                    padding="0.75em",
                    border_radius="12px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink=0,
                ),
                rx.vstack(
                    rx.text(
                        "Pass Percentage Configuration",
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Set the pass percentage for this assessment. This will be used to determine Pass/Fail status in all test reports and the overall report.",
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
            # Right: Input & Save & Decided by Facilitator
            rx.vstack(
                rx.text(
                    "Pass Percentage (%)",
                    font_family=FONT_BODY,
                    size="1",
                    color="#475467",
                    weight="medium",
                ),
                rx.hstack(
                    rx.input(
                        value=FacilitatorState.reports_pass_percentage,
                        on_change=FacilitatorState.set_reports_pass_percentage,
                        type="number",
                        min="0",
                        max="100",
                        width="110px",
                        size="2",
                        border_radius="8px",
                    ),
                    rx.button(
                        rx.icon("save", size=14),
                        "Save",
                        on_click=FacilitatorState.save_reports_pass_percentage,
                        size="2",
                        background="#4F46E5",
                        color="white",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        _hover={"background": "#4338CA"},
                        cursor="pointer",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Decided by Facilitator",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            width="100%",
            align_items="center",
        ),
        padding="1.3em 1.6em",
        border_radius="14px",
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        width="100%",
    )


def report_status_pill(status: str) -> rx.Component:
    return rx.match(
        status,
        (
            "Ready to Generate",
            rx.hstack(
                rx.icon("circle-check", size=13, color="#10B981"),
                rx.text(
                    "Ready to Generate",
                    font_family=FONT_BODY,
                    size="1",
                    color="#047857",
                    weight="medium",
                ),
                spacing="1",
                align_items="center",
                background="#ECFDF5",
                border="1px solid #A7F3D0",
                border_radius="20px",
                padding="0.25em 0.8em",
            ),
        ),
        (
            "Not Evaluated",
            rx.hstack(
                rx.icon("circle-alert", size=13, color="#F59E0B"),
                rx.text(
                    "Not Evaluated",
                    font_family=FONT_BODY,
                    size="1",
                    color="#B45309",
                    weight="medium",
                ),
                spacing="1",
                align_items="center",
                background="#FFFBEB",
                border="1px solid #FDE68A",
                border_radius="20px",
                padding="0.25em 0.8em",
            ),
        ),
        (
            "Not Available Yet",
            rx.hstack(
                rx.icon("info", size=13, color="#64748B"),
                rx.text(
                    "Not Available Yet",
                    font_family=FONT_BODY,
                    size="1",
                    color="#475467",
                    weight="medium",
                ),
                spacing="1",
                align_items="center",
                background="#F1F5F9",
                border="1px solid #CBD5E1",
                border_radius="20px",
                padding="0.25em 0.8em",
            ),
        ),
        # Default fallback
        rx.hstack(
            rx.icon("info", size=13, color="#64748B"),
            rx.text(status, font_family=FONT_BODY, size="1", color="#475467", weight="medium"),
            spacing="1",
            align_items="center",
            background="#F1F5F9",
            border="1px solid #CBD5E1",
            border_radius="20px",
            padding="0.25em 0.8em",
        ),
    )


def dynamic_test_report_card(item) -> rx.Component:
    """Render one report card from a dict — used by rx.foreach."""
    return rx.box(
        rx.hstack(
            # Left: Icon
            rx.box(
                rx.icon("file-text", size=22, color=item["icon_color"]),
                background=item["icon_bg"],
                padding="0.85em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Center: Info
            rx.vstack(
                rx.hstack(
                    rx.text(
                        item["title"],
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge(
                        item["badge_label"],
                        color_scheme=item["badge_scheme"],
                        variant="soft",
                        size="1",
                        border_radius="12px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.hstack(
                    rx.icon("calendar", size=13, color=COLORS["slate"]),
                    rx.text(
                        "Test Date: ",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    rx.text(
                        item["date_str"],
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="1",
                    align_items="center",
                ),
                rx.text(
                    item["description"],
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            # Divider
            rx.box(
                width="1px",
                height="56px",
                background="#F1F5F9",
                margin_x="0.6em",
                flex_shrink=0,
            ),
            # Status Column
            rx.vstack(
                rx.text(
                    "Status",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                report_status_pill(item["status"]),
                spacing="1",
                align_items="start",
                width="170px",
                flex_shrink=0,
            ),
            # Right: Action buttons
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=14, color="#4F46E5"),
                    "View Report",
                    on_click=FacilitatorState.view_report_action(item["title"]),
                    size="2",
                    variant="outline",
                    color_scheme="gray",
                    color="#4F46E5",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": "#F5F3FF"},
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download Report",
                    on_click=FacilitatorState.download_report_action(item["title"]),
                    size="2",
                    background="#4F46E5",
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": "#4338CA"},
                    cursor="pointer",
                ),
                spacing="2",
                align_items="center",
                flex_shrink=0,
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="1.2em 1.4em",
        border_radius="12px",
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        width="100%",
        _hover={"border_color": "#CBD5E1", "background": "#FAFAFC"},
        transition="all 0.15s ease",
    )


def test_report_card(
    title: str,
    badge_label: str,
    badge_scheme: str,
    icon_name: str,
    icon_color: str,
    icon_bg: str,
    date_str: str,
    description: str,
    status: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: Icon
            rx.box(
                rx.icon(icon_name, size=22, color=icon_color),
                background=icon_bg,
                padding="0.85em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Center: Info
            rx.vstack(
                rx.hstack(
                    rx.text(
                        title,
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge(
                        badge_label,
                        color_scheme=badge_scheme,
                        variant="soft",
                        size="1",
                        border_radius="12px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.hstack(
                    rx.icon("calendar", size=13, color=COLORS["slate"]),
                    rx.text(
                        "Test Date: ",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    rx.text(
                        date_str,
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    spacing="1",
                    align_items="center",
                ),
                rx.text(
                    description,
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            # Divider
            rx.box(
                width="1px",
                height="56px",
                background="#F1F5F9",
                margin_x="0.6em",
                flex_shrink=0,
            ),
            # Status Column
            rx.vstack(
                rx.text(
                    "Status",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                report_status_pill(status),
                spacing="1",
                align_items="start",
                width="170px",
                flex_shrink=0,
            ),
            # Right: Action buttons
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=14, color="#4F46E5"),
                    "View Report",
                    on_click=FacilitatorState.view_report_action(title),
                    size="2",
                    variant="outline",
                    color_scheme="gray",
                    color="#4F46E5",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": "#F5F3FF"},
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download Report",
                    on_click=FacilitatorState.download_report_action(title),
                    size="2",
                    background="#4F46E5",
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": "#4338CA"},
                    cursor="pointer",
                ),
                spacing="2",
                align_items="center",
                flex_shrink=0,
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="1.2em 1.4em",
        border_radius="12px",
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        width="100%",
        _hover={"border_color": "#CBD5E1", "background": "#FAFAFC"},
        transition="all 0.15s ease",
    )


def overall_report_card() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: Icon in green container
            rx.box(
                rx.icon("bar-chart-2", size=22, color="#059669"),
                background="#DCFCE7",
                padding="0.85em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Center: Info
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "Overall Assessment Report",
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge(
                        "Overall",
                        color_scheme="green",
                        variant="soft",
                        size="1",
                        border_radius="12px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Combined performance report across all tests based on configured assessment weightages.",
                    font_family=FONT_BODY,
                    size="2",
                    color="#475467",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            # Divider
            rx.box(
                width="1px",
                height="56px",
                background="#DCFCE7",
                margin_x="0.6em",
                flex_shrink=0,
            ),
            # Status Column
            rx.vstack(
                rx.text(
                    "Status",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                rx.cond(
                    FacilitatorState.can_show_overall_report,
                    report_status_pill("Ready to Generate"),
                    report_status_pill("Awaiting Evaluation / Weightage (100%)"),
                ),
                spacing="1",
                align_items="start",
                width="170px",
                flex_shrink=0,
            ),
            # Right: Action buttons
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=14, color=rx.cond(FacilitatorState.can_show_overall_report, "#4F46E5", COLORS["slate"])),
                    "View Report",
                    on_click=FacilitatorState.view_report_action("Overall Assessment Report"),
                    size="2",
                    variant="outline",
                    color_scheme="gray",
                    color=rx.cond(FacilitatorState.can_show_overall_report, "#4F46E5", COLORS["slate"]),
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": rx.cond(FacilitatorState.can_show_overall_report, "#F5F3FF", "white")},
                    cursor=rx.cond(FacilitatorState.can_show_overall_report, "pointer", "not-allowed"),
                    disabled=~FacilitatorState.can_show_overall_report,
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download Report",
                    on_click=FacilitatorState.download_report_action("Overall Assessment Report"),
                    size="2",
                    background=rx.cond(FacilitatorState.can_show_overall_report, "#4F46E5", "#CBD5E1"),
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": rx.cond(FacilitatorState.can_show_overall_report, "#4338CA", "#CBD5E1")},
                    cursor=rx.cond(FacilitatorState.can_show_overall_report, "pointer", "not-allowed"),
                    disabled=~FacilitatorState.can_show_overall_report,
                ),
                spacing="2",
                align_items="center",
                flex_shrink=0,
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="1.2em 1.4em",
        border="1px solid #BBF7D0",
        background="#F0FDF4",
        border_radius="12px",
        width="100%",
    )


def dynamic_test_report_card(item: dict) -> rx.Component:
    """A report card row for an individual test in the current assessment."""
    return rx.box(
        rx.hstack(
            # Left: Icon in blue/purple container
            rx.box(
                rx.icon(
                    rx.cond(item["is_final"], "award", "file-check"),
                    size=22,
                    color=rx.cond(item["is_final"], "#7C3AED", "#2563EB"),
                ),
                background=rx.cond(item["is_final"], "#EDE9FE", "#EFF6FF"),
                padding="0.85em",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink=0,
            ),
            # Center: Info
            rx.vstack(
                rx.hstack(
                    rx.text(
                        item["name"],
                        font_family=FONT_DISPLAY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge(
                        item["badge_label"],
                        color_scheme=item["badge_scheme"],
                        variant="soft",
                        size="1",
                        border_radius="12px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    item["description"],
                    font_family=FONT_BODY,
                    size="2",
                    color="#475467",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            # Divider
            rx.box(
                width="1px",
                height="56px",
                background="#E4E7EC",
                margin_x="0.6em",
                flex_shrink=0,
            ),
            # Status Column
            rx.vstack(
                rx.text(
                    "Status",
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    weight="medium",
                ),
                report_status_pill(item["status"]),
                spacing="1",
                align_items="start",
                width="170px",
                flex_shrink=0,
            ),
            # Right: Action buttons
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=14, color=rx.cond(item["is_ready"], "#4F46E5", COLORS["slate"])),
                    "View Report",
                    on_click=FacilitatorState.view_report_action(item["name"]),
                    size="2",
                    variant="outline",
                    color_scheme="gray",
                    color=rx.cond(item["is_ready"], "#4F46E5", COLORS["slate"]),
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": rx.cond(item["is_ready"], "#F5F3FF", "white")},
                    cursor=rx.cond(item["is_ready"], "pointer", "not-allowed"),
                    disabled=~item["is_ready"],
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download Report",
                    on_click=FacilitatorState.download_report_action(item["name"]),
                    size="2",
                    background=rx.cond(item["is_ready"], "#4F46E5", "#CBD5E1"),
                    color="white",
                    font_family=FONT_BODY,
                    border_radius="8px",
                    _hover={"background": rx.cond(item["is_ready"], "#4338CA", "#CBD5E1")},
                    cursor=rx.cond(item["is_ready"], "pointer", "not-allowed"),
                    disabled=~item["is_ready"],
                ),
                spacing="2",
                align_items="center",
                flex_shrink=0,
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="1.2em 1.4em",
        border="1px solid #E4E7EC",
        background="white",
        border_radius="12px",
        width="100%",
    )


def reports_tab() -> rx.Component:
    """Tab listing report cards for all tests + overall assessment report."""
    return rx.vstack(
        reports_header(),
        rx.box(height="0.5em"),
        # Section header
        rx.vstack(
            rx.text(
                "Available Reports",
                font_family=FONT_DISPLAY,
                size="4",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "View and download individual test reports or the overall assessment report.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            align_items="start",
            spacing="0",
            padding_bottom="0.8em",
        ),
        # Test Cards List
        rx.vstack(
            rx.cond(
                FacilitatorState.reports_dynamic_test_items.length() == 0,
                # Empty state
                rx.center(
                    rx.vstack(
                        rx.box(
                            background=COLORS["primary_soft"],
                            padding="1.2em",
                            border_radius="50%",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.text(
                            "No Tests Created Yet",
                            font_family=FONT_DISPLAY,
                            size="5",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.text(
                            "Create tests from the Tests tab to see report cards here.",
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                            text_align="center",
                        ),
                        align_items="center",
                        spacing="2",
                        padding="3em 2em",
                    ),
                    width="100%",
                    background=COLORS["surface"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="14px",
                ),
                # Has tests: render dynamically
                rx.vstack(
                    rx.foreach(
                        FacilitatorState.reports_dynamic_test_items,
                        dynamic_test_report_card,
                    ),
                    # Overall report card (always visible, showing dynamic status)
                    overall_report_card(),
                    spacing="3",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )


# ── Results Tab: Mini Category Bar Chart ──────────────────────────────────────

def _mini_bar_item(item: dict) -> rx.Component:
    """One bar in a mini category vertical bar chart."""
    return rx.vstack(
        # Score label above bar
        rx.text(
            item["score"].to_string(), "%",
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color=rx.cond(item["score"].to(float) >= 50, "#059669", "#DC2626"),
            text_align="center",
        ),
        # Bar
        rx.box(
            rx.box(
                position="absolute",
                bottom="0",
                left="0",
                right="0",
                style={"height": item["score"].to_string() + "%"},
                background=rx.cond(
                    item["score"].to(float) >= 80,
                    "linear-gradient(180deg, #6366F1 0%, #818CF8 100%)",
                    rx.cond(
                        item["score"].to(float) >= 50,
                        "linear-gradient(180deg, #3B82F6 0%, #60A5FA 100%)",
                        "linear-gradient(180deg, #EF4444 0%, #F87171 100%)",
                    ),
                ),
                border_radius="4px 4px 0 0",
                transition="height 0.4s ease",
            ),
            # 50% pass line
            rx.box(
                position="absolute",
                left="0",
                right="0",
                bottom="50%",
                border_top="1.5px dashed #EF4444",
                z_index="3",
            ),
            position="relative",
            width="28px",
            height="80px",
            background="#F1F5F9",
            border_radius="4px 4px 0 0",
            overflow="visible",
        ),
        # X label
        rx.text(
            item["name"],
            font_family=FONT_BODY,
            size="1",
            color=COLORS["slate"],
            text_align="center",
            max_width="48px",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        spacing="1",
        align_items="center",
    )


def _mini_category_chart(title: str, items, icon_name: str, icon_color: str, icon_bg: str) -> rx.Component:
    """Mini vertical bar chart card for CO / LO / Knowledge Type / Domain / RBT Level."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.box(
                    rx.icon(icon_name, size=14, color=icon_color),
                    background=icon_bg,
                    padding="0.35em",
                    border_radius="6px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
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
                padding_bottom="0.8em",
            ),
            # Bars — always rendered via foreach; shows empty state when list is empty
            rx.hstack(
                rx.foreach(items, _mini_bar_item),
                spacing="3",
                align_items="end",
                justify_content="center",
                padding_top="0.4em",
                min_height="100px",
                width="100%",
                overflow_x="auto",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em",
        flex="1",
        min_width="0",
    )


def _results_perf_summary_card() -> rx.Component:
    """Performance Summary card: Total Questions / Marks Obtained / Normalized Score / Status."""
    data = FacilitatorState.results_performance_summary
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("clipboard-check", size=14, color="#4F46E5"),
                    background="#EEF2FF",
                    padding="0.35em",
                    border_radius="6px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(
                    "Performance Summary",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                padding_bottom="0.8em",
            ),
            # Stat grid
            rx.grid(
                # Stat 1
                rx.vstack(
                    rx.text("Total Questions", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(data["total_questions"], font_family=FONT_DISPLAY, size="6", weight="bold", color=COLORS["ink"]),
                    spacing="0",
                    align_items="center",
                    padding="0.8em",
                    background="#F8FAFC",
                    border_radius="8px",
                ),
                # Stat 2
                rx.vstack(
                    rx.text("Marks Obtained", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(data["marks_str"], font_family=FONT_DISPLAY, size="5", weight="bold", color="#4F46E5"),
                    spacing="0",
                    align_items="center",
                    padding="0.8em",
                    background="#F8FAFC",
                    border_radius="8px",
                ),
                # Stat 3
                rx.vstack(
                    rx.text("Normalized Score", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.text(data["normalized_str"], font_family=FONT_DISPLAY, size="6", weight="bold", color="#059669"),
                    spacing="0",
                    align_items="center",
                    padding="0.8em",
                    background="#ECFDF5",
                    border_radius="8px",
                ),
                # Stat 4
                rx.vstack(
                    rx.text("Status", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                    rx.badge(
                        data["status"],
                        color_scheme=rx.cond(data["status"] == "Passed", "green", "red"),
                        variant="soft",
                        size="2",
                    ),
                    spacing="1",
                    align_items="center",
                    padding="0.8em",
                    background="#F8FAFC",
                    border_radius="8px",
                ),
                columns="2",
                spacing="2",
                width="100%",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em",
        flex="1",
        min_width="0",
    )


def _results_question_table_row(q: dict) -> rx.Component:
    """One row in the Question-wise Analysis table."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                "Q",
                q["q_no"].to_string(),
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
                text_align="center",
            ),
            text_align="center",
            width="70px",
        ),
        rx.table.cell(
            rx.text(
                q["question"],
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                white_space="normal",
                word_break="break-word",
            ),
        ),
        rx.table.cell(
            rx.text(
                q["marks_obtained"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["ink"],
                text_align="center",
            ),
            text_align="center",
            width="120px",
        ),
        rx.table.cell(
            rx.text(
                q["max_marks"].to_string(),
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
                text_align="center",
            ),
            text_align="center",
            width="100px",
        ),
        rx.table.cell(
            rx.text(
                q["score_pct"],
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=rx.cond(
                    q["score_pct_num"].to(float) >= FacilitatorState.results_pass_percentage,
                    "#059669",
                    "#DC2626",
                ),
                text_align="center",
            ),
            text_align="center",
            width="100px",
        ),
        rx.table.cell(
            rx.center(
                rx.box(
                    rx.text(
                        q["remarks"],
                        font_family=FONT_BODY,
                        size="1",
                        weight="bold",
                        color=q["r_color"],
                    ),
                    background=q["r_bg"],
                    border_radius="6px",
                    padding="0.2em 0.6em",
                    display="inline-flex",
                ),
                width="100%",
            ),
            text_align="center",
            width="120px",
        ),
        _hover={"background": "#F8FAFC"},
    )


def _results_qwise_bar_item(q: dict) -> rx.Component:
    """One vertical bar for question-wise score distribution chart."""
    return rx.box(
        # Score percentage above bar
        rx.text(
            q["score_pct"],
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color=rx.cond(
                q["score_pct_num"].to(float) >= FacilitatorState.results_pass_percentage,
                "#059669",
                "#DC2626",
            ),
            position="absolute",
            bottom=f"calc({q['score_pct_num']}% + 4px)",
            left="50%",
            transform="translateX(-50%)",
            white_space="nowrap",
            text_align="center",
            z_index="4",
        ),
        # Vertical bar itself anchored to baseline
        rx.box(
            position="absolute",
            bottom="0",
            left="50%",
            transform="translateX(-50%)",
            width="60%",
            max_width="42px",
            min_width="14px",
            style={"height": q["score_pct"]},
            background=rx.cond(
                q["score_pct_num"].to(float) >= FacilitatorState.results_pass_percentage,
                "#5B5BD6",
                "#EF4444",
            ),
            border_radius="4px 4px 0 0",
            transition="height 0.3s ease",
            z_index="2",
        ),
        # Q label beneath baseline
        rx.text(
            "Q",
            q["q_no"].to_string(),
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color=COLORS["slate"],
            position="absolute",
            top="100%",
            left="50%",
            transform="translateX(-50%)",
            padding_top="6px",
            white_space="nowrap",
            text_align="center",
        ),
        position="relative",
        flex="1",
        min_width="24px",
        max_width="56px",
        height="130px",
    )


def _results_question_analysis_section() -> rx.Component:
    """Question-wise Analysis view: Score Distribution bar chart + Question table."""
    return rx.vstack(
        # Header Row
        rx.hstack(
            rx.text(
                FacilitatorState.results_chart_title,
                font_family=FONT_BODY,
                size="2",
                weight="bold",
                color=COLORS["ink"],
                letter_spacing="0.02em",
            ),
            rx.spacer(),
            rx.text(
                "Score (%) = Marks Obtained / Max Marks × 100",
                font_family=FONT_BODY,
                size="1",
                color=COLORS["slate"],
            ),
            width="100%",
            align_items="center",
            padding_bottom="1.2em",
        ),

        # No data state
        rx.cond(
            FacilitatorState.results_question_analysis_items.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("list-x", size=28, color=COLORS["placeholder"]),
                    rx.text(
                        "Select a specific candidate and test to view question-wise analysis.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["placeholder"],
                        text_align="center",
                    ),
                    align_items="center",
                    spacing="2",
                    padding="2em",
                ),
                width="100%",
            ),

            # Content: 1. Bar chart, 2. Table
            rx.vstack(
                # 1. Score Distribution Bar Chart Card
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.hstack(
                                rx.icon("bar-chart-2", size=15, color=COLORS["primary"]),
                                rx.text(
                                    "Score Distribution",
                                    font_family=FONT_BODY,
                                    size="2",
                                    weight="bold",
                                    color=COLORS["ink"],
                                ),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.spacer(),
                            rx.hstack(
                                rx.box(width="16px", height="2px", background="#EF4444", border_radius="2px"),
                                rx.text(
                                    FacilitatorState.results_pass_percentage_str + " Pass Mark",
                                    font_family=FONT_BODY,
                                    size="1",
                                    weight="medium",
                                    color="#DC2626",
                                ),
                                spacing="2",
                                align_items="center",
                            ),
                            width="100%",
                            align_items="center",
                            padding_bottom="0.8em",
                        ),

                        # Chart Canvas with Y-axis
                        rx.hstack(
                            # Y-Axis Ticks
                            rx.vstack(
                                rx.text("100%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                rx.text("50%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                rx.text("0%", font_family=FONT_BODY, size="1", color="#94A3B8"),
                                style={"justify_content": "space-between"},
                                height="130px",
                                align_items="end",
                                padding_right="0.5em",
                                flex_direction="column",
                                display="flex",
                            ),
                            # Canvas Box
                            rx.box(
                                # Horizontal Gridlines
                                rx.box(position="absolute", left="0", right="0", top="0%", border_top="1px dashed #E2E8F0", z_index="1"),
                                rx.box(position="absolute", left="0", right="0", top="50%", border_top="1px dashed #E2E8F0", z_index="1"),
                                rx.box(position="absolute", left="0", right="0", bottom="0", border_top="1px solid #CBD5E1", z_index="1"),

                                # Dynamic Pass Mark line across chart
                                rx.box(
                                    position="absolute",
                                    left="0",
                                    right="0",
                                    top=FacilitatorState.results_pass_line_top,
                                    border_top="1.5px dashed #EF4444",
                                    z_index="2",
                                ),

                                # Bars row
                                rx.hstack(
                                    rx.foreach(
                                        FacilitatorState.results_question_analysis_items,
                                        _results_qwise_bar_item,
                                    ),
                                    style={"justify_content": "space-evenly"},
                                    align_items="end",
                                    height="130px",
                                    width="100%",
                                    z_index="4",
                                    position="relative",
                                    padding_x="0.8em",
                                ),

                                position="relative",
                                height="130px",
                                flex="1",
                                min_width="0",
                                border_left="1px solid #CBD5E1",
                                border_bottom="1px solid #CBD5E1",
                                margin_bottom="26px",
                            ),
                            spacing="1",
                            align_items="start",
                            width="100%",
                        ),

                        spacing="0",
                        width="100%",
                        align_items="stretch",
                    ),
                    background="#F8FAFC",
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    padding="1.2em",
                    width="100%",
                    margin_bottom="1.4em",
                ),

                # 2. Question-wise Analysis Table
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("Q. No.", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], text_align="center"),
                                    width="70px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Question", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]),
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Marks Obtained", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], text_align="center"),
                                    width="120px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Max Marks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], text_align="center"),
                                    width="100px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Score (%)", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], text_align="center"),
                                    width="100px",
                                ),
                                rx.table.column_header_cell(
                                    rx.text("Remarks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"], text_align="center"),
                                    width="120px",
                                ),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                FacilitatorState.results_question_analysis_items,
                                _results_question_table_row,
                            ),
                        ),
                        width="100%",
                    ),
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    overflow="hidden",
                    width="100%",
                ),

                spacing="0",
                width="100%",
                align_items="stretch",
            ),
        ),

        spacing="0",
        width="100%",
        align_items="stretch",
    )


def results_tab() -> rx.Component:
    """Redesigned Results Analytics tab matching the mockup."""
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
                disabled=~FacilitatorState.results_has_data,
            ),
            width="100%",
            align_items="center",
            padding_bottom="1.5em",
        ),

        # ── Filter Row: Candidate + Test + Status ─────────────────────
        rx.box(
            rx.hstack(
                # Select Candidate
                rx.hstack(
                    rx.text(
                        "Candidate:",
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
                            min_width="180px",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        padding="0.1em 0.5em",
                        align_items="center",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                # Select Test
                rx.hstack(
                    rx.text(
                        "Test:",
                        font_family=FONT_BODY,
                        size="2",
                        weight="medium",
                        color=COLORS["ink"],
                    ),
                    rx.hstack(
                        rx.icon("file-text", size=15, color=COLORS["slate"]),
                        rx.select(
                            FacilitatorState.results_test_options,
                            value=FacilitatorState.results_selected_test,
                            on_change=FacilitatorState.set_results_selected_test,
                            placeholder="All Tests",
                            size="2",
                            variant="surface",
                            min_width="160px",
                        ),
                        background=COLORS["surface"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        padding="0.1em 0.5em",
                        align_items="center",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                # Eval status badge (only when a specific cand + test is selected)
                rx.cond(
                    FacilitatorState.results_eval_status != "",
                    rx.hstack(
                        rx.badge(
                            FacilitatorState.results_eval_status,
                            color_scheme=rx.cond(
                                FacilitatorState.results_eval_status == "Evaluated",
                                "green",
                                "gray",
                            ),
                            variant="soft",
                            size="2",
                        ),
                        rx.cond(
                            FacilitatorState.results_eval_date != "",
                            rx.text(
                                "Submitted on " + FacilitatorState.results_eval_date,
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            rx.box(),
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.box(),
                ),
                spacing="4",
                align_items="center",
                wrap="wrap",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="10px",
            padding="0.8em 1.2em",
            width="100%",
        ),

        # ── Analytics ─────────────────────────────────────────────────
        rx.cond(
            FacilitatorState.results_has_data,

            # Has data: Tab-specific visualization only
            rx.vstack(
                results_performance_analysis_card(),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),

            # No data: empty state
            rx.center(
                rx.vstack(
                    rx.box(
                        rx.icon("bar-chart-2", size=40, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="1.2em",
                        border_radius="50%",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text(
                        "No Results Available",
                        font_family=FONT_DISPLAY,
                        size="5",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "AI evaluation has not been run yet for the selected candidate and test.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                        text_align="center",
                    ),
                    rx.text(
                        "Go to the Evaluation tab, select a candidate, and run AI Evaluation to see results here.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["placeholder"],
                        text_align="center",
                    ),
                    rx.button(
                        rx.icon("pencil-line", size=14),
                        "Go to Evaluation",
                        on_click=FacilitatorState.set_workspace_tab("evaluation"),
                        size="2",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        border_radius="8px",
                        _hover={"background": COLORS["primary_hover"]},
                        margin_top="0.5em",
                    ),
                    align_items="center",
                    spacing="2",
                    padding="4em 2em",
                ),
                width="100%",
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="14px",
            ),
        ),

        spacing="4",
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

def qp_upload_dialog() -> rx.Component:
    """Dialog modal for uploading or replacing question paper for the selected test."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.dialog.title(
                            rx.cond(
                                FacilitatorState.has_current_test_qp,
                                "Replace Question Paper",
                                "Upload Question Paper",
                            ),
                            font_family=FONT_DISPLAY,
                            size="4",
                            weight="bold",
                            color=COLORS["ink"],
                        ),
                        rx.dialog.description(
                            rx.hstack(
                                rx.text("Assessment: ", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                rx.text(FacilitatorState.selected_assessment_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                rx.text(" • Test: ", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                rx.text(FacilitatorState.selected_test_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["primary"]),
                                spacing="1",
                                align_items="center",
                            ),
                        ),
                        spacing="1",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=18),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=FacilitatorState.cancel_replacing_qp,
                        ),
                    ),
                    width="100%",
                    align_items="start",
                    padding_bottom="0.5em",
                ),
                active_test_dropzone_card(),
                spacing="3",
                width="100%",
            ),
            style={"maxWidth": "620px", "width": "92vw", "padding": "1.8em", "borderRadius": "16px"},
        ),
        open=FacilitatorState.is_replacing_qp,
        on_open_change=FacilitatorState.set_is_replacing_qp,
    )



# ──────────────────────────────────────────────────────────────────────────────
# Report Detail Tab  (opened via "View Report" from the Reports tab)
# ──────────────────────────────────────────────────────────────────────────────

def _report_nav_item(label: str, icon_name: str, sec_id: str, section_key: str) -> rx.Component:
    is_active = (FacilitatorState.active_report_section == section_key)
    return rx.box(
        rx.hstack(
            rx.icon(
                icon_name,
                size=16,
                color=rx.cond(is_active, COLORS["primary"], COLORS["slate"]),
            ),
            rx.text(
                label,
                font_family=FONT_BODY,
                size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, COLORS["primary"], "#334155"),
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="0.65em 0.9em",
        border_radius="8px",
        background=rx.cond(is_active, "#F3E8FF", "transparent"),
        cursor="pointer",
        transition="all 0.15s ease",
        _hover={"background": rx.cond(is_active, "#F3E8FF", "#F8FAFC")},
        on_click=[
            FacilitatorState.set_active_report_section(section_key),
            rx.call_script(f"const el = document.getElementById('{sec_id}'); if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});"),
        ],
        width="100%",
    )


def _report_doc_section_banner(icon_name: str, title: str, sec_id: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon(icon_name, size=15, color="#4F46E5"),
            rx.text(title, font_family=FONT_BODY, size="2", weight="bold", color="#1E293B"),
            spacing="2",
            align_items="center",
        ),
        id=sec_id,
        background="#EEF2FF",
        border="1px solid #E0E7FF",
        border_radius="6px",
        padding="0.5em 0.85em",
        width="100%",
        margin_top="1.8em",
        margin_bottom="0.8em",
    )


def _report_candidate_status_pill(status: str) -> rx.Component:
    return rx.match(
        status,
        ("Passed", rx.box(rx.text("Passed", font_family=FONT_BODY, size="1", weight="bold", color="#03543F"), background="#DEF7EC", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Failed", rx.box(rx.text("Failed", font_family=FONT_BODY, size="1", weight="bold", color="#9B1C1C"), background="#FDE8E8", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        rx.box(rx.text("Pending", font_family=FONT_BODY, size="1", weight="bold", color="#854D0E"), background="#FEF08A", border_radius="12px", padding="0.2em 0.8em", display="inline-flex"),
    )


def _report_difficulty_pill(diff: str) -> rx.Component:
    return rx.match(
        diff,
        ("Easy", rx.box(rx.text("Easy", font_family=FONT_BODY, size="1", weight="bold", color="#03543F"), background="#DEF7EC", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Medium", rx.box(rx.text("Medium", font_family=FONT_BODY, size="1", weight="bold", color="#92400E"), background="#FEF3C7", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Hard", rx.box(rx.text("Hard", font_family=FONT_BODY, size="1", weight="bold", color="#9B1C1C"), background="#FDE8E8", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        rx.text(diff, font_family=FONT_BODY, size="2", color="#475467"),
    )




# --- Direct Report Document Print Script ---
# Generates PDF/print directly from the report document content in an isolated iframe,
# completely excluding viewer toolbars, dark viewer frame, app chrome, and blank pages.
_REPORT_PRINT_SCRIPT = """
(function() {
    window.printReportDocument = function() {
        var report = document.getElementById('report-printable-doc');
        if (!report) {
            window.print();
            return;
        }

        var existing = document.getElementById('report-print-frame');
        if (existing) {
            existing.remove();
        }

        var iframe = document.createElement('iframe');
        iframe.id = 'report-print-frame';
        iframe.style.position = 'fixed';
        iframe.style.top = '-9999px';
        iframe.style.left = '-9999px';
        iframe.style.width = '210mm';
        iframe.style.height = '297mm';
        iframe.style.border = 'none';
        document.body.appendChild(iframe);

        var doc = iframe.contentWindow.document;

        var headContent = '';
        document.querySelectorAll('link[rel="stylesheet"], style').forEach(function(el) {
            if (!el.innerText || !el.innerText.includes('@media print')) {
                headContent += el.outerHTML;
            }
        });

        var printStyle = `
            <style>
                @page {
                    size: A4 portrait;
                    margin: 8mm 12mm 8mm 12mm;
                }
                * {
                    box-sizing: border-box !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                html, body {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                    color: #0F172A !important;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
                    font-size: 13px !important;
                    line-height: 1.35 !important;
                    width: 100% !important;
                    height: auto !important;
                }
                #report-printable-doc {
                    width: 100% !important;
                    max-width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                    box-shadow: none !important;
                    border: none !important;
                }
                [id^="sec-"] {
                    margin-top: 10px !important;
                    margin-bottom: 5px !important;
                    padding: 3px 8px !important;
                }
                table, .rt-TableRoot {
                    margin-bottom: 6px !important;
                    width: 100% !important;
                    font-size: 11.5px !important;
                }
                td, th, .rt-TableCell, .rt-TableColumnHeaderCell {
                    padding: 3px 6px !important;
                }
                tr, table, .rt-TableRoot, [id^="sec-"] {
                    break-inside: avoid !important;
                    page-break-inside: avoid !important;
                }
            </style>
        `;

        var cloned = report.cloneNode(true);
        cloned.style.boxShadow = 'none';
        cloned.style.border = 'none';
        cloned.style.padding = '0';
        cloned.style.margin = '0';
        cloned.style.width = '100%';
        cloned.style.maxWidth = '100%';

        doc.open();
        doc.write('<!DOCTYPE html><html><head><title>' + (document.title || 'Assessment Report') + '</title>' + headContent + printStyle + '</head><body>' + cloned.outerHTML + '</body></html>');
        doc.close();

        setTimeout(function() {
            try {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            } catch (e) {
                window.print();
            }
        }, 350);
    };

    if (!window.__printReportDocListenerAdded) {
        window.__printReportDocListenerAdded = true;
        window.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) {
                var reportDoc = document.getElementById('report-printable-doc');
                if (reportDoc) {
                    e.preventDefault();
                    window.printReportDocument();
                }
            }
        });
    }
})();
"""

# --- Fallback Main Document Print CSS for Report View ---
_REPORT_PRINT_STYLE = """
@media print {
    @page {
        size: A4 portrait;
        margin: 8mm 12mm 8mm 12mm;
    }
    * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    header, nav, aside, button,
    #pdf-viewer-toolbar,
    #report-nav-sidebar,
    [data-report-chrome="true"],
    .rt-DialogOverlay,
    .rt-DialogContent {
        display: none !important;
    }
    html, body {
        height: auto !important;
        overflow: visible !important;
        background: #ffffff !important;
    }
    body * {
        visibility: hidden !important;
    }
    #report-printable-doc,
    #report-printable-doc * {
        visibility: visible !important;
    }
    #report-printable-doc {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        border: none !important;
        background: #ffffff !important;
    }
    [id^="sec-"] {
        margin-top: 10px !important;
        margin-bottom: 5px !important;
        padding: 3px 8px !important;
    }
    table, .rt-TableRoot {
        margin-bottom: 6px !important;
        width: 100% !important;
        font-size: 11.5px !important;
    }
    td, th, .rt-TableCell, .rt-TableColumnHeaderCell {
        padding: 3px 6px !important;
    }
    tr, table, .rt-TableRoot, [id^="sec-"] {
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }
}
"""


def report_detail_tab() -> rx.Component:
    """Detailed report page matching reference design — driven entirely by real state data."""
    stats = FacilitatorState.report_summary_stats
    meta = FacilitatorState.report_metadata

    return rx.vstack(
        rx.script(_REPORT_PRINT_SCRIPT),
        rx.html(f"<style>{_REPORT_PRINT_STYLE}</style>"),
        # ── 1. Top Bar: Back to Reports link ───────────────────────────────────
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=14),
                "Back to Reports",
                on_click=FacilitatorState.back_to_reports,
                variant="ghost",
                color=COLORS["primary"],
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                cursor="pointer",
                _hover={"background": COLORS["primary_soft"]},
                border_radius="8px",
                padding_x="0.5em",
                padding_y="0.3em",
            ),
            width="100%",
            align_items="center",
            margin_bottom="0.4em",
            data_report_chrome="true",
        ),

        # ── 2. Header Row: Title, badge, subtitle, and Print/Download buttons ──
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        FacilitatorState.selected_report_test_name,
                        " Report",
                        font_family=FONT_DISPLAY,
                        size="6",
                        weight="bold",
                        color="#0F172A",
                    ),
                    rx.badge(
                        meta["badge"],
                        color_scheme=meta["badge_scheme"],
                        variant="soft",
                        size="2",
                        border_radius="12px",
                        padding_x="0.7em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.text(
                    "Detailed performance report for ",
                    FacilitatorState.selected_report_test_name,
                    ".",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("printer", size=14),
                    "Print",
                    variant="outline",
                    color="#1E293B",
                    font_family=FONT_BODY,
                    size="2",
                    weight="medium",
                    border="1px solid #CBD5E1",
                    background="white",
                    border_radius="8px",
                    cursor="pointer",
                    padding_x="1em",
                    _hover={"background": "#F8FAFC", "border_color": "#94A3B8"},
                    on_click=rx.call_script("if (window.printReportDocument) window.printReportDocument(); else window.print();"),
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download PDF",
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    size="2",
                    weight="medium",
                    border_radius="8px",
                    cursor="pointer",
                    padding_x="1.2em",
                    _hover={"background": COLORS["primary_hover"]},
                    on_click=[
                        FacilitatorState.download_report_action(""),
                        rx.call_script("if (window.printReportDocument) window.printReportDocument(); else window.print();"),
                    ],
                ),
                spacing="3",
                align_items="center",
            ),
            width="100%",
            align_items="center",
            margin_bottom="1.5em",
            data_report_chrome="true",
        ),

        # ── 3. Main Split View: Left Navigation + Right PDF Viewer ─────────────
        rx.hstack(
            # ── Left Navigation Sidebar Card ──────────────────────────────────
            rx.box(
                rx.vstack(
                    _report_nav_item("Report Summary", "file-text", "sec-summary", "summary"),
                    _report_nav_item("Candidate Performance", "users", "sec-candidates", "candidates"),
                    _report_nav_item("Pass/Fail Summary", "circle-check", "sec-passfail", "passfail"),
                    _report_nav_item("Remarks", "message-square", "sec-remarks", "remarks"),
                    spacing="1",
                    width="100%",
                    align_items="stretch",
                ),
                background="white",
                border="1px solid #E2E8F0",
                border_radius="12px",
                padding="1em 0.8em",
                width="240px",
                min_width="240px",
                box_shadow="0 1px 3px rgba(0,0,0,0.04)",
                id="report-nav-sidebar",
            ),

            # ── Right Report Document Preview ─────────────────────────────────
            rx.box(
                rx.vstack(
                                # TVS Document Header
                                rx.hstack(
                                    rx.image(
                                        src="/tvs_logo.png",
                                        height="34px",
                                        width="auto",
                                        object_fit="contain",
                                    ),
                                    rx.spacer(),
                                    rx.text(
                                        "GEN AI HYBRID EVALUATOR",
                                        font_family=FONT_BODY,
                                        size="3",
                                        weight="bold",
                                        color="#1E293B",
                                        letter_spacing="0.04em",
                                    ),
                                    rx.spacer(),
                                    rx.text(
                                        "Assessment Report",
                                        font_family=FONT_BODY,
                                        size="3",
                                        weight="bold",
                                        color="#1E293B",
                                    ),
                                    width="100%",
                                    align_items="center",
                                ),
                                rx.box(width="100%", height="1px", background="#E2E8F0", margin_y="1.2em"),

                                # Report Metadata Header
                                rx.hstack(
                                    rx.vstack(
                                        rx.text(
                                            FacilitatorState.selected_report_test_name,
                                            " Report",
                                            font_family=FONT_DISPLAY,
                                            size="6",
                                            weight="bold",
                                            color="#0F172A",
                                        ),
                                        rx.text(
                                            FacilitatorState.selected_assessment_name,
                                            " Assessment",
                                            font_family=FONT_BODY,
                                            size="2",
                                            weight="bold",
                                            color="#334155",
                                        ),
                                        rx.text(
                                            "Assessment Type: ",
                                            meta["badge"],
                                            font_family=FONT_BODY,
                                            size="2",
                                            color="#64748B",
                                        ),
                                        spacing="1",
                                        align_items="start",
                                    ),
                                    rx.spacer(),
                                    rx.vstack(
                                        rx.hstack(
                                            rx.text("Test Date", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["test_date"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.hstack(
                                            rx.text("Generated On", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["generated_on"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.hstack(
                                            rx.text("Generated By", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["generated_by"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        spacing="1",
                                        align_items="start",
                                    ),
                                    width="100%",
                                    align_items="start",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 1: Assessment Summary ──────────────
                                _report_doc_section_banner("file-text", "Assessment Summary", "sec-summary"),
                                rx.box(
                                    rx.hstack(
                                        # Left column
                                        rx.vstack(
                                            rx.hstack(
                                                rx.text("Total Candidates", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["total"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Evaluated", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["evaluated"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Pending", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["pending"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            spacing="3",
                                            flex="1",
                                            align_items="stretch",
                                        ),
                                        # Divider
                                        rx.box(width="1px", background="#E2E8F0", margin_x="2em", align_self="stretch"),
                                        # Right column
                                        rx.vstack(
                                            rx.hstack(
                                                rx.text("Pass Percentage (Set by Facilitator)", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["pass_pct"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Candidates Passed", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["passed"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Candidates Failed", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["failed"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            spacing="3",
                                            flex="1",
                                            align_items="stretch",
                                        ),
                                        width="100%",
                                        align_items="start",
                                    ),
                                    background="#F8FAFC",
                                    border="1px solid #E2E8F0",
                                    border_radius="6px",
                                    padding="1.2em 1.5em",
                                    width="100%",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 2: Candidate Performance ───────────
                                _report_doc_section_banner("users", "Candidate Performance", "sec-candidates"),
                                rx.cond(
                                    FacilitatorState.report_candidate_rows.length() == 0,
                                    rx.box(
                                        rx.text("No candidates assigned to this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                        padding="1em",
                                    ),
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell(rx.text("#", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Candidate ID", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Candidate Name", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Normalized Score (%)", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Weightage (%)", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Weighted Score", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Status", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                            ),
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                FacilitatorState.report_candidate_rows,
                                                lambda row: rx.table.row(
                                                    rx.table.cell(rx.text(row["idx"], font_family=FONT_BODY, size="2", color="#64748B")),
                                                    rx.table.cell(rx.text(row["cand_id"], font_family=FONT_BODY, size="2", color="#334155")),
                                                    rx.table.cell(rx.text(row["cand_name"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium")),
                                                    rx.table.cell(rx.text(row["score_str"], font_family=FONT_BODY, size="2", color="#0F172A", weight="bold")),
                                                    rx.table.cell(rx.text(row["weightage_str"], font_family=FONT_BODY, size="2", color="#475467")),
                                                    rx.table.cell(rx.text(row["weighted_score_str"], font_family=FONT_BODY, size="2", color="#6C3FF4", weight="bold")),
                                                    rx.table.cell(_report_candidate_status_pill(row["status"])),
                                                ),
                                            ),
                                        ),
                                        width="100%",
                                        variant="surface",
                                        margin_bottom="1.2em",
                                    ),
                                ),

                                # ── Section 3: Pass / Fail Summary ─────────────
                                _report_doc_section_banner("circle-check", "Pass/Fail Summary", "sec-passfail"),
                                rx.box(
                                    rx.hstack(
                                        rx.vstack(
                                            rx.text("Passed", font_family=FONT_BODY, size="2", color="#059669", weight="medium"),
                                            rx.text(stats["passed"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#059669"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.vstack(
                                            rx.text("Failed", font_family=FONT_BODY, size="2", color="#DC2626", weight="medium"),
                                            rx.text(stats["failed"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#DC2626"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.vstack(
                                            rx.text("Pending", font_family=FONT_BODY, size="2", color="#D97706", weight="medium"),
                                            rx.text(stats["pending"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#D97706"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        spacing="8",
                                        justify="center",
                                        width="100%",
                                    ),
                                    background="#F8FAFC",
                                    border="1px solid #E2E8F0",
                                    border_radius="6px",
                                    padding="1.5em",
                                    width="100%",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 5: Remarks ─────────────────────────
                                _report_doc_section_banner("message-square", "Remarks", "sec-remarks"),
                                rx.cond(
                                    FacilitatorState.report_remarks_rows.length() == 0,
                                    rx.box(
                                        rx.text("No remarks available yet. Remarks are populated from evaluation feedback.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                        padding="1em",
                                    ),
                                    rx.vstack(
                                        rx.foreach(
                                            FacilitatorState.report_remarks_rows,
                                            lambda row: rx.box(
                                                rx.vstack(
                                                    rx.text(row["candidate"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                                    rx.text(row["remarks"], font_family=FONT_BODY, size="2", color="#475467", line_height="1.6"),
                                                    spacing="1",
                                                    align_items="start",
                                                ),
                                                background="#F8FAFC",
                                                border="1px solid #E2E8F0",
                                                border_left=f"3px solid {COLORS['primary']}",
                                                border_radius="6px",
                                                padding="0.9em 1.2em",
                                                width="100%",
                                            ),
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                ),

                                spacing="0",
                                width="100%",
                                align_items="stretch",
                            ),
                            background="white",
                            border="1px solid #E2E8F0",
                            border_radius="12px",
                            box_shadow="0 1px 3px rgba(0,0,0,0.05)",
                            padding="2.5em 3em",
                            flex="1",
                            min_width="0",
                            width="100%",
                            id="report-printable-doc",
                        ),

            spacing="5",
            width="100%",
            align_items="start",
        ),

        spacing="0",
        width="100%",
        align_items="stretch",
    )


def assessment_workspace_page() -> rx.Component:
    content = rx.vstack(
        rx.match(
            FacilitatorState.active_workspace_tab,
            ("tests", tests_tab()),
            ("question_paper", tests_tab()),
            ("evaluation", evaluation_tab()),
            ("weightage", weightage_tab()),
            ("results", results_tab()),
            ("reports", reports_tab()),
            ("report_detail", report_detail_tab()),
            # Fallback
            tests_tab(),
        ),
        qp_preview_dialog(),
        qp_upload_dialog(),
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
