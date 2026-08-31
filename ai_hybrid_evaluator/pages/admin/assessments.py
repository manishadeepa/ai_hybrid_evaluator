"""Assessments page — list + Add / Edit / Delete Assessment + Tests Management & Details (mock data)."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.models.models import Candidate, Facilitator
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def test_chip(assessment_index: int, test_name: str) -> rx.Component:
    """Clickable test badge shown directly under the assessment name."""
    return rx.badge(
        rx.icon("file-text", size=11),
        test_name,
        color_scheme="indigo",
        variant="soft",
        size="1",
        cursor="pointer",
        font_family=FONT_BODY,
        on_click=AdminState.open_test_details(assessment_index, test_name),
        _hover={"background": COLORS["primary_soft"], "color": COLORS["primary"]},
    )


def final_test_chip(assessment_index: int, final_test_name: str) -> rx.Component:
    """Clickable final test badge shown directly under the assessment name."""
    return rx.badge(
        rx.icon("award", size=11),
        final_test_name,
        color_scheme="amber",
        variant="soft",
        size="1",
        cursor="pointer",
        font_family=FONT_BODY,
        on_click=AdminState.open_test_details(assessment_index, final_test_name),
        _hover={"background": "#FEF3C7", "color": "#B45309"},
    )


def facilitator_response_badge(approval_status: str) -> rx.Component:
    """Shows the facilitator's Approve/Decline response for the admin to see."""
    return rx.match(
        approval_status,
        ("approved", rx.hstack(
            rx.icon("circle-check", size=13, color="#027A48"),
            rx.text("Approved", font_family=FONT_BODY, size="1", weight="medium", color="#027A48"),
            spacing="1",
            align_items="center",
            background="#ECFDF3",
            border="1px solid #A6F4C5",
            padding="0.3em 0.7em",
            border_radius="999px",
        )),
        ("declined", rx.hstack(
            rx.icon("circle-x", size=13, color="#991B1B"),
            rx.text("Declined", font_family=FONT_BODY, size="1", weight="medium", color="#991B1B"),
            spacing="1",
            align_items="center",
            background="#FEF2F2",
            border="1px solid #FECACA",
            padding="0.3em 0.7em",
            border_radius="999px",
        )),
        # Default — pending / awaiting
        rx.hstack(
            rx.icon("clock", size=13, color="#B45309"),
            rx.text("Awaiting", font_family=FONT_BODY, size="1", weight="medium", color="#B45309"),
            spacing="1",
            align_items="center",
            background="#FFFBEB",
            border="1px solid #FDE68A",
            padding="0.3em 0.7em",
            border_radius="999px",
        ),
    )


def assessment_row(a: dict, idx: int) -> rx.Component:
    return rx.table.row(
        # 1. Assessment & Tests
        rx.table.cell(
            rx.vstack(
                rx.text(
                    a["name"],
                    font_family=FONT_BODY,
                    color=COLORS["ink"],
                    weight="bold",
                    size="3",
                ),
                rx.hstack(
                    rx.foreach(
                        a["tests"],
                        lambda t: test_chip(idx, t),
                    ),
                    final_test_chip(idx, a["final_test"]),
                    spacing="1",
                    wrap="wrap",
                    align_items="center",
                    padding_top="0.2em",
                ),
                spacing="1",
                align_items="start",
            )
        ),
        # 2. Facilitator
        rx.table.cell(a["facilitator_name"], font_family=FONT_BODY, color=COLORS["slate"]),
        # 3. Candidates
        rx.table.cell(
            rx.text(
                a["assigned_candidates"].length().to_string() + " candidates",
                font_family=FONT_BODY, color=COLORS["slate"], size="2",
            ),
        ),
        # 4. Tests count
        rx.table.cell(
            rx.text(
                a["tests"].length().to_string() + " + Final",
                font_family=FONT_BODY, color=COLORS["slate"], size="2",
            ),
        ),
        # 5. Status
        rx.table.cell(
            rx.match(
                a["status"],
                ("Scheduled", rx.badge("Scheduled", color_scheme="orange", variant="soft", size="1", font_family=FONT_BODY)),
                ("Active", rx.badge("Active", color_scheme="indigo", variant="soft", size="1", font_family=FONT_BODY)),
                ("Completed", rx.badge("Completed", color_scheme="green", variant="soft", size="1", font_family=FONT_BODY)),
                rx.badge("Draft", color_scheme="gray", variant="soft", size="1", font_family=FONT_BODY),
            ),
        ),
        # 6. Actions (Type of Test / Edit / Delete)
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("list-plus", size=14),
                    "Type of Test",
                    on_click=AdminState.open_assessment_tests(idx),
                    size="1",
                    variant="soft",
                    color_scheme="indigo",
                    font_family=FONT_BODY,
                ),
                rx.button(
                    rx.icon("pencil", size=14),
                    "Edit",
                    on_click=AdminState.open_edit_assessment(idx),
                    size="1",
                    variant="outline",
                    color=COLORS["ink"],
                    background=COLORS["surface"],
                    border=f"1px solid {COLORS['line']}",
                    font_family=FONT_BODY,
                    _hover={"background": COLORS["canvas"]},
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    "Delete",
                    on_click=AdminState.open_delete_assessment(idx),
                    size="1",
                    color=COLORS["danger"],
                    background="#FEE4E2",
                    border="1px solid #FDA29B",
                    font_family=FONT_BODY,
                    _hover={"background": "#FECDCA"},
                ),
                spacing="2",
                justify="center",
                width="100%",
            ),
            justify="center",
            align="center",
        ),
        # 7. Facilitator Response (Approved / Awaiting / Declined)
        rx.table.cell(
            facilitator_response_badge(a.get("approval_status", "pending")),
        ),
    )



# ─────────────────────────────────────────────────────────────
# Searchable Facilitator Items & Dropdowns
# ─────────────────────────────────────────────────────────────

def add_facilitator_item(f: Facilitator) -> rx.Component:
    is_selected = AdminState.new_assessment_facilitator_id == f["emp_id"]
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(f["name"], font_family=FONT_BODY, color=COLORS["ink"], size="2", weight="medium"),
                rx.text(f["emp_id"] + " · " + f["email"], font_family=FONT_BODY, color=COLORS["slate"], size="1"),
                spacing="0", align_items="start",
            ),
            rx.spacer(),
            rx.cond(
                is_selected,
                rx.icon("check", size=15, color=COLORS["primary"]),
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.5em 0.6em",
        border_radius="6px",
        cursor="pointer",
        background=rx.cond(is_selected, COLORS["primary_soft"], "transparent"),
        _hover={"background": rx.cond(is_selected, COLORS["primary_soft"], COLORS["canvas"])},
        on_click=AdminState.select_add_facilitator(f["emp_id"]),
        width="100%",
    )


def edit_facilitator_item(f: Facilitator) -> rx.Component:
    is_selected = AdminState.edit_assessment_facilitator_id == f["emp_id"]
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(f["name"], font_family=FONT_BODY, color=COLORS["ink"], size="2", weight="medium"),
                rx.text(f["emp_id"] + " · " + f["email"], font_family=FONT_BODY, color=COLORS["slate"], size="1"),
                spacing="0", align_items="start",
            ),
            rx.spacer(),
            rx.cond(
                is_selected,
                rx.icon("check", size=15, color=COLORS["primary"]),
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.5em 0.6em",
        border_radius="6px",
        cursor="pointer",
        background=rx.cond(is_selected, COLORS["primary_soft"], "transparent"),
        _hover={"background": rx.cond(is_selected, COLORS["primary_soft"], COLORS["canvas"])},
        on_click=AdminState.select_edit_facilitator(f["emp_id"]),
        width="100%",
    )


def add_facilitator_select() -> rx.Component:
    """Searchable facilitator selection control for Create Assessment."""
    return rx.vstack(
        rx.hstack(
            rx.cond(
                AdminState.new_assessment_facilitator_id == "",
                rx.text("Select Facilitator", font_family=FONT_BODY, size="2", color=COLORS["placeholder"]),
                rx.text(AdminState.selected_add_facilitator_name, font_family=FONT_BODY, size="2", color=COLORS["ink"], weight="medium"),
            ),
            rx.spacer(),
            rx.icon(
                rx.cond(AdminState.show_add_facilitator_dropdown, "chevron-up", "chevron-down"),
                size=15, color=COLORS["slate"],
            ),
            width="100%",
            align_items="center",
            padding="0.5em 0.75em",
            border=f"1px solid {COLORS['line']}",
            border_radius="8px",
            cursor="pointer",
            background=COLORS["surface"],
            on_click=AdminState.toggle_add_facilitator_dropdown,
            _hover={"border_color": COLORS["primary"]},
        ),
        rx.cond(
            AdminState.show_add_facilitator_dropdown,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("search", size=14, color=COLORS["slate"]),
                        rx.input(
                            placeholder="Search facilitator...",
                            value=AdminState.add_facilitator_search,
                            on_change=AdminState.set_add_facilitator_search,
                            size="1",
                            variant="surface",
                            width="100%",
                            font_family=FONT_BODY,
                        ),
                        align_items="center",
                        padding="0.4em 0.5em",
                        border_bottom=f"1px solid {COLORS['line']}",
                        width="100%",
                        spacing="2",
                    ),
                    rx.cond(
                        AdminState.filtered_add_facilitators.length() == 0,
                        rx.text("No facilitators found", font_family=FONT_BODY, size="2", color=COLORS["slate"], padding="0.8em", text_align="center"),
                        rx.box(
                            rx.foreach(AdminState.filtered_add_facilitators, add_facilitator_item),
                            max_height="180px",
                            overflow_y="auto",
                            width="100%",
                            padding="0.3em",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                border=f"1px solid {COLORS['line']}",
                border_radius="8px",
                width="100%",
                background=COLORS["surface"],
                box_shadow="0 4px 12px rgba(0,0,0,0.08)",
            ),
        ),
        spacing="1",
        width="100%",
        align_items="stretch",
    )


def edit_facilitator_select() -> rx.Component:
    """Searchable facilitator selection control for Edit Assessment."""
    return rx.vstack(
        rx.hstack(
            rx.cond(
                AdminState.edit_assessment_facilitator_id == "",
                rx.text("Select Facilitator", font_family=FONT_BODY, size="2", color=COLORS["placeholder"]),
                rx.text(AdminState.selected_edit_facilitator_name, font_family=FONT_BODY, size="2", color=COLORS["ink"], weight="medium"),
            ),
            rx.spacer(),
            rx.icon(
                rx.cond(AdminState.show_edit_facilitator_dropdown, "chevron-up", "chevron-down"),
                size=15, color=COLORS["slate"],
            ),
            width="100%",
            align_items="center",
            padding="0.5em 0.75em",
            border=f"1px solid {COLORS['line']}",
            border_radius="8px",
            cursor="pointer",
            background=COLORS["surface"],
            on_click=AdminState.toggle_edit_facilitator_dropdown,
            _hover={"border_color": COLORS["primary"]},
        ),
        rx.cond(
            AdminState.show_edit_facilitator_dropdown,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("search", size=14, color=COLORS["slate"]),
                        rx.input(
                            placeholder="Search facilitator...",
                            value=AdminState.edit_facilitator_search,
                            on_change=AdminState.set_edit_facilitator_search,
                            size="1",
                            variant="surface",
                            width="100%",
                            font_family=FONT_BODY,
                        ),
                        align_items="center",
                        padding="0.4em 0.5em",
                        border_bottom=f"1px solid {COLORS['line']}",
                        width="100%",
                        spacing="2",
                    ),
                    rx.cond(
                        AdminState.filtered_edit_facilitators.length() == 0,
                        rx.text("No facilitators found", font_family=FONT_BODY, size="2", color=COLORS["slate"], padding="0.8em", text_align="center"),
                        rx.box(
                            rx.foreach(AdminState.filtered_edit_facilitators, edit_facilitator_item),
                            max_height="180px",
                            overflow_y="auto",
                            width="100%",
                            padding="0.3em",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                border=f"1px solid {COLORS['line']}",
                border_radius="8px",
                width="100%",
                background=COLORS["surface"],
                box_shadow="0 4px 12px rgba(0,0,0,0.08)",
            ),
        ),
        spacing="1",
        width="100%",
        align_items="stretch",
    )


# ─────────────────────────────────────────────────────────────
# Candidate Checkbox Rows
# ─────────────────────────────────────────────────────────────

def add_candidate_checkbox_row(c: Candidate) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=AdminState.new_assessment_candidate_ids.contains(c["emp_id"]),
                on_change=lambda checked: AdminState.toggle_new_assessment_candidate(c["emp_id"], checked),
            ),
            rx.vstack(
                rx.text(c["name"], font_family=FONT_BODY, color=COLORS["ink"], size="2", weight="medium"),
                rx.text(c["emp_id"] + " · " + c["email"], font_family=FONT_BODY, color=COLORS["slate"], size="1"),
                spacing="0", align_items="start",
            ),
            spacing="3", align_items="center", width="100%",
        ),
        padding="0.5em 0.4em",
        border_bottom=f"1px solid {COLORS['line']}",
        width="100%",
    )


def edit_candidate_checkbox_row(c: Candidate) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=AdminState.edit_assessment_candidate_ids.contains(c["emp_id"]),
                on_change=lambda checked: AdminState.toggle_edit_assessment_candidate(c["emp_id"], checked),
            ),
            rx.vstack(
                rx.text(c["name"], font_family=FONT_BODY, color=COLORS["ink"], size="2", weight="medium"),
                rx.text(c["emp_id"] + " · " + c["email"], font_family=FONT_BODY, color=COLORS["slate"], size="1"),
                spacing="0", align_items="start",
            ),
            spacing="3", align_items="center", width="100%",
        ),
        padding="0.5em 0.4em",
        border_bottom=f"1px solid {COLORS['line']}",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────
# Type of Test / Assessment Tests Dialog (Add / Remove Tests)
# ─────────────────────────────────────────────────────────────

def test_card(item: dict) -> rx.Component:
    test_name = item["name"]
    test_date = item["date"]
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("file-text", size=16, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="0.5em",
                border_radius="8px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(test_name, font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    rx.badge("Regular", color_scheme="indigo", variant="soft", size="1"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text("Regular Assessment Stage", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),
            rx.spacer(),
            # Date picker
            rx.vstack(
                rx.text("Date", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                rx.input(
                    type="date",
                    value=test_date,
                    on_change=lambda v: AdminState.set_test_date(test_name, v),
                    size="1",
                    width="160px",
                    font_family=FONT_BODY,
                ),
                spacing="1",
                align_items="start",
            ),
            rx.cond(
                test_name != "Test 1",
                rx.button(
                    rx.icon("trash-2", size=13),
                    on_click=AdminState.remove_test_from_selected_assessment(test_name),
                    size="1",
                    variant="ghost",
                    color=COLORS["danger"],
                    _hover={"background": "#FEE4E2"},
                ),
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.75em 1em",
        border=f"1px solid {COLORS['line']}",
        border_radius="10px",
        background=COLORS["surface"],
        width="100%",
    )


def assessment_tests_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("layers", size=20, color=COLORS["primary"]),
                    rx.text(
                        AdminState.current_tests_assessment_name + " — Type of Test",
                        font_family=FONT_BODY,
                        color=COLORS["ink"],
                    ),
                    spacing="2",
                    align_items="center",
                )
            ),
            rx.dialog.description(
                "Configure multiple regular tests and the main final test for this assessment.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                # ── Regular Tests Section ─────────────────────────────
                rx.hstack(
                    rx.vstack(
                        rx.text("Regular Tests", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                        rx.text("Tests administered progressively before the final evaluation.", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                        spacing="0",
                        align_items="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("plus", size=14),
                        "Add Test",
                        on_click=AdminState.add_test_to_selected_assessment,
                        size="1",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        _hover={"background": COLORS["primary_hover"]},
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="0.5em",
                ),
                rx.vstack(
                    rx.foreach(AdminState.current_assessment_tests_with_dates, test_card),
                    spacing="2",
                    width="100%",
                    max_height="220px",
                    overflow_y="auto",
                    padding_right="0.2em",
                ),

                # ── Divider ───────────────────────────────────────────
                rx.box(height="1px", background=COLORS["line"], width="100%", margin="0.8em 0"),

                # ── Final Test Section ────────────────────────────────
                rx.vstack(
                    rx.text("Final Test", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                    rx.text("The one main comprehensive final evaluation test.", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                    padding_bottom="0.5em",
                    width="100%",
                ),
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("award", size=20, color="#B45309"),
                            background="#FEF3C7",
                            padding="0.6em",
                            border_radius="10px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.text(
                                    AdminState.current_assessment_final_test,
                                    font_family=FONT_BODY,
                                    size="2",
                                    weight="bold",
                                    color=COLORS["ink"],
                                ),
                                rx.badge("Main Final Evaluation", color_scheme="amber", variant="soft", size="1"),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.text("Mandatory cumulative assessment stage", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.spacer(),
                        # Date picker for Final Test
                        rx.vstack(
                            rx.text("Date", font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                            rx.input(
                                type="date",
                                value=AdminState.current_assessment_final_test_date,
                                on_change=lambda v: AdminState.set_test_date(AdminState.current_assessment_final_test, v),
                                size="1",
                                width="160px",
                                font_family=FONT_BODY,
                            ),
                            spacing="1",
                            align_items="start",
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    padding="0.85em 1em",
                    border="1px solid #FCD34D",
                    border_radius="10px",
                    background="#FFFDF5",
                    width="100%",
                ),
                spacing="1",
                width="100%",
                align_items="stretch",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "Done",
                        variant="solid",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        _hover={"background": COLORS["primary_hover"]},
                    )
                ),
                padding_top="1.4em",
                width="100%",
            ),
            style={"maxWidth": "480px"},
        ),
        open=AdminState.show_assessment_tests_dialog,
        on_open_change=AdminState.set_show_assessment_tests_dialog,
    )


# ─────────────────────────────────────────────────────────────
# Test Details / Updates Dialog (When Clicking a Test Badge)
# ─────────────────────────────────────────────────────────────

def test_details_candidate_row(c: Candidate) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("user", size=14, color=COLORS["primary"]),
                background=COLORS["primary_soft"],
                padding="0.4em",
                border_radius="6px",
            ),
            rx.vstack(
                rx.text(c["name"], font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                rx.text(c["emp_id"] + " · " + c["email"], font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                spacing="0",
                align_items="start",
            ),
            rx.spacer(),
            rx.badge("Enrolled", color_scheme="green", variant="soft", size="1"),
            width="100%",
            align_items="center",
        ),
        padding="0.5em 0.6em",
        border_bottom=f"1px solid {COLORS['line']}",
        width="100%",
    )


def test_details_dialog() -> rx.Component:
    """Shows real-time updates and assignment details when clicking a test badge."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.cond(
                        AdminState.viewing_test_is_final,
                        rx.icon("award", size=20, color="#B45309"),
                        rx.icon("file-text", size=20, color=COLORS["primary"]),
                    ),
                    rx.text(
                        AdminState.viewing_test_assessment_name + " — " + AdminState.viewing_test_name,
                        font_family=FONT_BODY,
                        color=COLORS["ink"],
                        weight="bold",
                    ),
                    rx.cond(
                        AdminState.viewing_test_is_final,
                        rx.badge("Final Test", color_scheme="amber", variant="soft", size="1"),
                        rx.badge("Regular Test", color_scheme="indigo", variant="soft", size="1"),
                    ),
                    spacing="2",
                    align_items="center",
                )
            ),
            rx.dialog.description(
                "Test status, handling facilitator, and enrolled candidates list.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                # ── Handling Facilitator Card ─────────────────────────
                rx.text("Facilitator Handling", size="2", weight="bold", color=COLORS["ink"], font_family=FONT_BODY),
                rx.box(
                    rx.hstack(
                        rx.box(
                            rx.icon("user-cog", size=18, color=COLORS["primary"]),
                            background=COLORS["primary_soft"],
                            padding="0.6em",
                            border_radius="8px",
                        ),
                        rx.vstack(
                            rx.text(
                                AdminState.viewing_test_facilitator_name,
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                AdminState.viewing_test_facilitator_id + " · " + AdminState.viewing_test_facilitator_email,
                                font_family=FONT_BODY,
                                size="1",
                                color=COLORS["slate"],
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.badge("Active Facilitator", color_scheme="indigo", variant="soft", size="1"),
                        width="100%",
                        align_items="center",
                    ),
                    padding="0.75em 0.9em",
                    border=f"1px solid {COLORS['line']}",
                    border_radius="10px",
                    background=COLORS["surface"],
                    width="100%",
                ),

                # ── Date & Stage Info ─────────────────────────────────
                rx.hstack(
                    rx.box(
                        rx.vstack(
                            rx.text("Scheduled Date", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                            rx.text(AdminState.viewing_test_date, font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                            spacing="0",
                        ),
                        padding="0.6em 0.8em",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        background=COLORS["surface"],
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Stage Type", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                            rx.cond(
                                AdminState.viewing_test_is_final,
                                rx.text("Main Evaluation", font_family=FONT_BODY, size="2", weight="medium", color="#B45309"),
                                rx.text("Progressive Assessment", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
                            ),
                            spacing="0",
                        ),
                        padding="0.6em 0.8em",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        background=COLORS["surface"],
                        flex="1",
                    ),
                    width="100%",
                    spacing="2",
                    padding_top="0.4em",
                ),

                # ── Assigned Candidates Section ───────────────────────
                rx.hstack(
                    rx.text("Assigned Candidates", size="2", weight="bold", color=COLORS["ink"], font_family=FONT_BODY),
                    rx.spacer(),
                    rx.text(
                        AdminState.viewing_test_candidates_list.length().to_string() + " candidate(s)",
                        font_family=FONT_BODY, size="1", color=COLORS["slate"],
                    ),
                    width="100%",
                    align_items="center",
                    padding_top="0.8em",
                ),
                rx.cond(
                    AdminState.viewing_test_candidates_list.length() == 0,
                    rx.text("No candidates assigned to this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"], padding="0.8em", text_align="center"),
                    rx.box(
                        rx.foreach(AdminState.viewing_test_candidates_list, test_details_candidate_row),
                        max_height="180px",
                        overflow_y="auto",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        padding="0.2em 0.6em",
                        width="100%",
                        background=COLORS["surface"],
                    ),
                ),
                spacing="2",
                width="100%",
                align_items="stretch",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "Close",
                        variant="solid",
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        _hover={"background": COLORS["primary_hover"]},
                    )
                ),
                padding_top="1.4em",
                width="100%",
            ),
            style={"maxWidth": "480px"},
        ),
        open=AdminState.show_test_details_dialog,
        on_open_change=AdminState.set_show_test_details_dialog,
    )


# ─────────────────────────────────────────────────────────────
# Add Assessment Dialog
# ─────────────────────────────────────────────────────────────

def add_assessment_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=16),
                "Create Assessment",
                background=COLORS["primary"],
                color="white",
                border_radius="8px",
                font_family=FONT_BODY,
                _hover={"background": COLORS["primary_hover"]},
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Create Assessment", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.dialog.description(
                "Set up an assessment and assign it to a facilitator and candidates.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                # ── 1. Assessment Name ────────────────────────────────
                rx.text("Assessment Name", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                rx.input(
                    placeholder="e.g. Q3 Technical Assessment",
                    value=AdminState.new_assessment_name,
                    on_change=AdminState.set_new_assessment_name,
                    width="100%",
                ),
                # ── 2. Facilitator (Searchable) ───────────────────────
                rx.text("Facilitator", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                add_facilitator_select(),
                # ── 4. Candidates (Searchable Multi-select) ───────────
                rx.text("Candidates", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.vstack(
                    # Trigger row — click to open/close the checkbox panel
                    rx.hstack(
                        rx.cond(
                            AdminState.new_assessment_candidate_ids.length() == 0,
                            rx.text("Select Candidates", font_family=FONT_BODY, size="2", color=COLORS["placeholder"]),
                            rx.text(
                                AdminState.new_assessment_candidate_ids.length().to_string() + " candidate(s) selected",
                                font_family=FONT_BODY, size="2", color=COLORS["ink"], weight="medium",
                            ),
                        ),
                        rx.spacer(),
                        rx.icon(
                            rx.cond(AdminState.show_add_candidate_dropdown, "chevron-up", "chevron-down"),
                            size=15, color=COLORS["slate"],
                        ),
                        width="100%",
                        align_items="center",
                        padding="0.5em 0.75em",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        cursor="pointer",
                        background=COLORS["surface"],
                        on_click=AdminState.toggle_add_candidate_dropdown,
                        _hover={"border_color": COLORS["primary"]},
                    ),
                    # Checkbox panel with Search bar — only visible when open
                    rx.cond(
                        AdminState.show_add_candidate_dropdown,
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("search", size=14, color=COLORS["slate"]),
                                    rx.input(
                                        placeholder="Search candidates...",
                                        value=AdminState.add_candidate_search,
                                        on_change=AdminState.set_add_candidate_search,
                                        size="1",
                                        variant="surface",
                                        width="100%",
                                        font_family=FONT_BODY,
                                    ),
                                    align_items="center",
                                    padding="0.4em 0.5em",
                                    border_bottom=f"1px solid {COLORS['line']}",
                                    width="100%",
                                    spacing="2",
                                ),
                                rx.cond(
                                    AdminState.filtered_add_candidates.length() == 0,
                                    rx.text("No candidates found", font_family=FONT_BODY, size="2", color=COLORS["slate"], padding="0.8em", text_align="center"),
                                    rx.box(
                                        rx.foreach(AdminState.filtered_add_candidates, add_candidate_checkbox_row),
                                        max_height="200px",
                                        overflow_y="auto",
                                        width="100%",
                                        padding="0.2em 0.6em",
                                    ),
                                ),
                                spacing="0",
                                width="100%",
                            ),
                            border=f"1px solid {COLORS['line']}",
                            border_radius="8px",
                            width="100%",
                            background=COLORS["surface"],
                            box_shadow="0 4px 12px rgba(0,0,0,0.08)",
                        ),
                    ),
                    spacing="1",
                    width="100%",
                    align_items="stretch",
                ),
                # ── Validation error ──────────────────────────────────
                rx.cond(
                    AdminState.assessment_form_error != "",
                    rx.text(AdminState.assessment_form_error, color=COLORS["danger"], size="2", font_family=FONT_BODY, padding_top="0.7em"),
                ),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.hstack(
                rx.dialog.close(rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY)),
                rx.button(
                    "Create", on_click=AdminState.add_assessment,
                    background=COLORS["primary"], color="white", font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                ),
                spacing="3", justify="end", padding_top="1.6em", width="100%",
            ),
            style={"maxWidth": "460px"},
        ),
        open=AdminState.show_add_assessment,
        on_open_change=AdminState.set_show_add_assessment,
    )


# ─────────────────────────────────────────────────────────────
# Edit Assessment Dialog
# ─────────────────────────────────────────────────────────────

def edit_assessment_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Assessment", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.dialog.description(
                "Update this assessment's details and assignments.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                rx.text("Assessment Name", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                rx.input(
                    value=AdminState.edit_assessment_name,
                    on_change=AdminState.set_edit_assessment_name,
                    width="100%",
                ),
                rx.text("Facilitator", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                edit_facilitator_select(),
                rx.text("Candidates", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.vstack(
                    rx.hstack(
                        rx.icon("search", size=14, color=COLORS["slate"]),
                        rx.input(
                            placeholder="Search candidates...",
                            value=AdminState.edit_candidate_search,
                            on_change=AdminState.set_edit_candidate_search,
                            size="1",
                            variant="surface",
                            width="100%",
                            font_family=FONT_BODY,
                        ),
                        align_items="center",
                        padding="0.4em 0.5em",
                        border=f"1px solid {COLORS['line']}",
                        border_radius="8px",
                        width="100%",
                        spacing="2",
                        background=COLORS["surface"],
                    ),
                    rx.cond(
                        AdminState.filtered_edit_candidates.length() == 0,
                        rx.text("No candidates found", font_family=FONT_BODY, size="2", color=COLORS["slate"], padding="0.8em", text_align="center"),
                        rx.box(
                            rx.foreach(AdminState.filtered_edit_candidates, edit_candidate_checkbox_row),
                            max_height="200px",
                            overflow_y="auto",
                            border=f"1px solid {COLORS['line']}",
                            border_radius="8px",
                            padding="0.2em 0.8em",
                            width="100%",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                    align_items="stretch",
                ),
                rx.cond(
                    AdminState.edit_assessment_error != "",
                    rx.text(AdminState.edit_assessment_error, color=COLORS["danger"], size="2", font_family=FONT_BODY, padding_top="0.7em"),
                ),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.hstack(
                rx.dialog.close(rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY)),
                rx.button(
                    "Save Changes", on_click=AdminState.save_edit_assessment,
                    background=COLORS["primary"], color="white", font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                ),
                spacing="3", justify="end", padding_top="1.6em", width="100%",
            ),
            style={"maxWidth": "460px"},
        ),
        open=AdminState.show_edit_assessment,
        on_open_change=AdminState.set_show_edit_assessment,
    )


# ─────────────────────────────────────────────────────────────
# Delete Assessment Dialog
# ─────────────────────────────────────────────────────────────

def delete_assessment_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Remove assessment?", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.alert_dialog.description(
                "Are you sure you want to remove " + AdminState.delete_assessment_name + "? This action cannot be undone.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY,
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Remove", on_click=AdminState.confirm_delete_assessment,
                        background=COLORS["danger"], color="white", font_family=FONT_BODY,
                    ),
                ),
                spacing="3", justify="end", padding_top="1.4em", width="100%",
            ),
            style={"maxWidth": "380px"},
        ),
        open=AdminState.show_delete_assessment,
        on_open_change=AdminState.set_show_delete_assessment,
    )


# ─────────────────────────────────────────────────────────────
# Assessments Page
# ─────────────────────────────────────────────────────────────

def assessments_page() -> rx.Component:
    content = rx.vstack(
        rx.hstack(
            rx.text(
                AdminState.total_assessments.to_string() + " assessments",
                font_family=FONT_BODY, color=COLORS["slate"], size="2",
            ),
            rx.spacer(),
            add_assessment_dialog(),
            width="100%", align_items="center",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Assessment & Tests"),
                        rx.table.column_header_cell("Facilitator"),
                        rx.table.column_header_cell("Candidates"),
                        rx.table.column_header_cell("Tests"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Actions", justify="center", align="center"),
                        rx.table.column_header_cell("Facilitator Response"),
                    ),
                ),
                rx.table.body(rx.foreach(AdminState.assessments, assessment_row)),
                width="100%",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="0.5em",
            margin_top="1.2em",
            width="100%",
        ),
        assessment_tests_dialog(),
        test_details_dialog(),
        edit_assessment_dialog(),
        delete_assessment_dialog(),
        width="100%",
    )
    return admin_shell(
        active="assessments",
        title="Assessments",
        subtitle="Create assessments and assign them to facilitators and candidates.",
        content=content,
    )