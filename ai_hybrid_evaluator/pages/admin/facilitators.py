"""Facilitators page — list + Add / Edit / Delete Facilitator (mock data)."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def facilitator_row(f: dict, idx: int) -> rx.Component:
    return rx.table.row(
        rx.table.cell(f["emp_id"], font_family=FONT_BODY, color=COLORS["slate"]),
        rx.table.cell(f["name"], font_family=FONT_BODY, color=COLORS["ink"]),
        rx.table.cell(f["email"], font_family=FONT_BODY, color=COLORS["slate"]),
        rx.table.cell(f["phone"], font_family=FONT_BODY, color=COLORS["slate"]),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=14),
                    "View Profile",
                    on_click=AdminState.open_view_facilitator_profile(idx),
                    size="1",
                    variant="outline",
                    color=COLORS["primary"],
                    background=COLORS["surface"],
                    border=f"1px solid {COLORS['primary']}",
                    font_family=FONT_BODY,
                    _hover={"background": COLORS["canvas"]},
                ),
                rx.button(
                    rx.icon("pencil", size=14),
                    "Edit",
                    on_click=AdminState.open_edit_facilitator(idx),
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
                    on_click=AdminState.open_delete_facilitator(idx),
                    size="1",
                    color=COLORS["danger"],
                    background="#FEE4E2",
                    border="1px solid #FDA29B",
                    font_family=FONT_BODY,
                    _hover={"background": "#FECDCA"},
                ),
                spacing="2",
            ),
        ),
    )


def add_facilitator_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=16),
                "Add Facilitator",
                background=COLORS["primary"],
                color="white",
                border_radius="8px",
                font_family=FONT_BODY,
                _hover={"background": COLORS["primary_hover"]},
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add Facilitator", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.dialog.description(
                "The facilitator will be able to sign in once created.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                rx.text("Facilitator ID", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                rx.input(
                    placeholder="e.g. F001",
                    value=AdminState.new_facilitator_empid,
                    on_change=AdminState.set_new_facilitator_empid,
                    max_length=4,
                    width="100%",
                ),
                rx.text(
                    "Format: F followed by 3 digits (F001–F999)",
                    size="1", color=COLORS["placeholder"], font_family=FONT_BODY, padding_top="0.2em",
                ),
                rx.text("Facilitator Name", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    placeholder="Full Name",
                    value=AdminState.new_facilitator_name,
                    on_change=AdminState.set_new_facilitator_name,
                    width="100%",
                ),
                rx.text("Facilitator Mail", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    placeholder="name@tvsmotor.com",
                    value=AdminState.new_facilitator_email,
                    on_change=AdminState.set_new_facilitator_email,
                    width="100%",
                ),
                rx.text("Facilitator Phone", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    placeholder="Phone Number",
                    value=AdminState.new_facilitator_phone,
                    on_change=AdminState.set_new_facilitator_phone,
                    max_length=10,
                    width="100%",
                ),
                rx.text("Password", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    type="password",
                    placeholder="Set a password for this facilitator",
                    value=AdminState.new_facilitator_password,
                    on_change=AdminState.set_new_facilitator_password,
                    width="100%",
                ),
                rx.cond(
                    AdminState.facilitator_form_error != "",
                    rx.text(AdminState.facilitator_form_error, color=COLORS["danger"], size="2", font_family=FONT_BODY, padding_top="0.7em"),
                ),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.hstack(
                rx.dialog.close(rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY)),
                rx.button(
                    "Create", on_click=AdminState.add_facilitator,
                    background=COLORS["primary"], color="white", font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                ),
                spacing="3", justify="end", padding_top="1.6em", width="100%",
            ),
            style={"maxWidth": "420px"},
        ),
        open=AdminState.show_add_facilitator,
        on_open_change=AdminState.set_show_add_facilitator,
    )


def edit_facilitator_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Facilitator", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.dialog.description(
                "Update this facilitator's details.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY, padding_bottom="1.2em",
            ),
            rx.vstack(
                rx.text("Facilitator ID", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY),
                rx.input(
                    value=AdminState.edit_facilitator_empid,
                    on_change=AdminState.set_edit_facilitator_empid,
                    max_length=4,
                    width="100%",
                ),
                rx.text(
                    "Format: F followed by 3 digits (F001–F999)",
                    size="1", color=COLORS["placeholder"], font_family=FONT_BODY, padding_top="0.2em",
                ),
                rx.text("Facilitator Name", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    value=AdminState.edit_facilitator_name,
                    on_change=AdminState.set_edit_facilitator_name,
                    width="100%",
                ),
                rx.text("Facilitator Mail", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    value=AdminState.edit_facilitator_email,
                    on_change=AdminState.set_edit_facilitator_email,
                    width="100%",
                ),
                rx.text("Facilitator Phone", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    value=AdminState.edit_facilitator_phone,
                    on_change=AdminState.set_edit_facilitator_phone,
                    max_length=10,
                    width="100%",
                ),
                rx.text("Password", size="2", weight="medium", color=COLORS["ink"], font_family=FONT_BODY, padding_top="0.9em"),
                rx.input(
                    type="password",
                    value=AdminState.edit_facilitator_password,
                    on_change=AdminState.set_edit_facilitator_password,
                    width="100%",
                ),
                rx.cond(
                    AdminState.edit_facilitator_error != "",
                    rx.text(AdminState.edit_facilitator_error, color=COLORS["danger"], size="2", font_family=FONT_BODY, padding_top="0.7em"),
                ),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.hstack(
                rx.dialog.close(rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY)),
                rx.button(
                    "Save Changes", on_click=AdminState.save_edit_facilitator,
                    background=COLORS["primary"], color="white", font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                ),
                spacing="3", justify="end", padding_top="1.6em", width="100%",
            ),
            style={"maxWidth": "420px"},
        ),
        open=AdminState.show_edit_facilitator,
        on_open_change=AdminState.set_show_edit_facilitator,
    )


def delete_facilitator_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Remove facilitator?", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.alert_dialog.description(
                "Are you sure you want to remove " + AdminState.delete_facilitator_name + "? This action cannot be undone.",
                size="2", color=COLORS["slate"], font_family=FONT_BODY,
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="outline", color=COLORS["slate"], font_family=FONT_BODY),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Remove", on_click=AdminState.confirm_delete_facilitator,
                        background=COLORS["danger"], color="white", font_family=FONT_BODY,
                    ),
                ),
                spacing="3", justify="end", padding_top="1.4em", width="100%",
            ),
            style={"maxWidth": "380px"},
        ),
        open=AdminState.show_delete_facilitator,
        on_open_change=AdminState.set_show_delete_facilitator,
    )

def _profile_info_item(label: str, value: rx.Var, icon_name: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon_name, size=13, color=COLORS["slate"]),
                rx.text(label, font_family=FONT_BODY, size="1", color=COLORS["slate"], weight="medium"),
                spacing="1",
                align_items="center",
            ),
            rx.text(
                rx.cond(value != "", value, "—"),
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["ink"],
            ),
            spacing="1",
            align_items="start",
        ),
        background="#F8FAFC",
        padding="0.6em 0.8em",
        border_radius="8px",
        border=f"1px solid {COLORS['line']}",
        width="100%",
    )


def view_facilitator_profile_dialog() -> rx.Component:
    p = AdminState.viewing_facilitator_profile
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header row with avatar and basic info
                rx.hstack(
                    rx.avatar(
                        src=rx.cond(
                            p["profile_photo_url"] != "",
                            p["profile_photo_url"],
                            "/placeholder_avatar.png",
                        ),
                        fallback="FA",
                        size="6",
                        radius="full",
                        color_scheme="indigo",
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.text(p["full_name"], font_family=FONT_BODY, size="4", weight="bold", color=COLORS["ink"]),
                            rx.badge(p["emp_id"], color_scheme="indigo", size="1"),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.text(
                            p["designation"],
                            font_family=FONT_BODY,
                            size="2",
                            color=COLORS["slate"],
                        ),
                        spacing="1",
                    ),
                    spacing="4",
                    align_items="center",
                    padding_bottom="1.2em",
                    border_bottom=f"1px solid {COLORS['line']}",
                    width="100%",
                ),
                
                # Details Grid in a scrollable container
                rx.vstack(
                    rx.text("Contact Information", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], padding_top="0.8em"),
                    rx.grid(
                        _profile_info_item("Email", p["email"], "mail"),
                        _profile_info_item("Phone", p["phone"], "phone"),
                        _profile_info_item("Location", p["location"], "map-pin"),
                        _profile_info_item("Availability", p["availability"], "clock"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    
                    rx.text("Professional & Organization", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], padding_top="1em"),
                    rx.grid(
                        _profile_info_item("Department", p["department"], "building-2"),
                        _profile_info_item("Business Unit", p["business_unit"], "briefcase"),
                        _profile_info_item("Years of Exp.", p["years_experience"], "award"),
                        _profile_info_item("Training Exp.", p["training_experience"], "users"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    
                    rx.text("Domain & Expertise", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"], padding_top="1em"),
                    rx.grid(
                        _profile_info_item("Primary Expertise", p["primary_expertise"], "circle-check"),
                        _profile_info_item("Domain / Subjects", p["subjects_domains"], "book-open"),
                        _profile_info_item("Specific Skills", p["specific_skills"], "cpu"),
                        _profile_info_item("Education", p["highest_qualification"], "graduation-cap"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    _profile_info_item("Specialization", p["specialization"], "file-text"),
                    _profile_info_item("Certifications", p["certifications"], "award"),
                    spacing="2",
                    width="100%",
                    max_height="55vh",
                    overflow_y="auto",
                    padding_right="0.5em",
                ),
                
                # Footer Close Button
                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            variant="outline",
                            color=COLORS["slate"],
                            font_family=FONT_BODY,
                            on_click=AdminState.close_view_facilitator_profile,
                        ),
                    ),
                    width="100%",
                    padding_top="1.2em",
                    border_top=f"1px solid {COLORS['line']}",
                ),
                spacing="3",
                width="100%",
            ),
            style={"maxWidth": "620px"},
        ),
        open=AdminState.show_view_facilitator_profile,
        on_open_change=AdminState.set_show_view_facilitator_profile,
    )


def facilitators_page() -> rx.Component:
    content = rx.vstack(
        rx.hstack(
            rx.text(
                AdminState.total_facilitators.to_string() + " facilitators",
                font_family=FONT_BODY, color=COLORS["slate"], size="2",
            ),
            rx.spacer(),
            add_facilitator_dialog(),
            width="100%", align_items="center",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("FID", width="12%"),
                        rx.table.column_header_cell("Name", width="18%"),
                        rx.table.column_header_cell("Email", width="30%"),
                        rx.table.column_header_cell("Phone", width="15%"),
                        rx.table.column_header_cell("Actions", width="25%"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AdminState.facilitators, facilitator_row),
                ),
                width="100%",
                table_layout="fixed",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="0.5em",
            margin_top="1.2em",
            width="100%",
        ),
        view_facilitator_profile_dialog(),
        edit_facilitator_dialog(),
        delete_facilitator_dialog(),
        width="100%",
    )
    return admin_shell(
        active="facilitators",
        title="Facilitators",
        subtitle="Manage facilitator accounts and access.",
        content=content,
    )