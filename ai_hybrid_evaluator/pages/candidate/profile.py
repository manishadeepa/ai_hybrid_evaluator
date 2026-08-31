"""Candidate Profile Page — matching Facilitator Profile layout and styling exactly."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.candidate_shell import candidate_shell
from ai_hybrid_evaluator.state.candidate_state import CandidateProfileState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


def form_field(label: str, placeholder: str, value: rx.Var, on_change, type: str = "text") -> rx.Component:
    return rx.vstack(
        rx.text(label, font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=type,
            width="100%",
            size="3",
            background=COLORS["surface"],
            border=f"1.5px solid {COLORS['line']}",
            _focus={"border_color": COLORS["primary"], "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}"},
        ),
        spacing="1",
        width="100%",
    )


def form_select(label: str, placeholder: str, options: list[str], value: rx.Var, on_change) -> rx.Component:
    return rx.vstack(
        rx.text(label, font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
        rx.select(
            options,
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            width="100%",
            size="3",
            color_scheme="gray",
        ),
        spacing="1",
        width="100%",
    )


def section_header(title: str) -> rx.Component:
    return rx.box(
        rx.text(title, font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
        border_bottom=f"1px solid {COLORS['line']}",
        padding_bottom="0.5em",
        margin_top="1.5em",
        margin_bottom="1em",
        width="100%",
    )


def profile_page_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            # ── Profile Photo Row ──────────────────────────────────────
            rx.hstack(
                rx.avatar(
                    src=CandidateProfileState.profile_photo_url,
                    fallback=CandidateProfileState.full_name[:2].upper(),
                    size="7",
                    radius="full",
                    color_scheme="indigo",
                ),
                rx.vstack(
                    rx.text("Profile Photo", font_family=FONT_BODY, size="3", weight="bold", color=COLORS["ink"]),
                    rx.upload(
                        rx.hstack(
                            rx.icon("upload", size=14, color=COLORS["primary"]),
                            rx.text("Upload Photo", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["primary"]),
                            spacing="2",
                            align_items="center",
                            padding="0.5em 1em",
                            border=f"1px solid {COLORS['primary']}",
                            border_radius="8px",
                            background="transparent",
                            cursor="pointer",
                            _hover={"background": COLORS["canvas"]},
                        ),
                        id="candidate_profile_photo_uploader",
                        accept="image/png,image/jpeg,image/jpg",
                        max_files=1,
                        border="none",
                        padding="0",
                        cursor="pointer",
                        on_drop=CandidateProfileState.handle_photo_upload(
                            rx.upload_files(upload_id="candidate_profile_photo_uploader")
                        ),
                    ),
                    align_items="start",
                    spacing="2",
                ),
                spacing="4",
                align_items="center",
                margin_bottom="1.5em",
            ),

            # ── 1. Employee Information Section ────────────────────────
            section_header("Employee Information"),
            rx.grid(
                form_field("Full Name", "Enter your full name", CandidateProfileState.full_name, CandidateProfileState.set_full_name),
                form_field("Employee ID", "e.g. CAND-2031", CandidateProfileState.emp_id, CandidateProfileState.set_emp_id),
                form_field("Official Email", "Enter your official email", CandidateProfileState.email, CandidateProfileState.set_email, "email"),
                form_field("Phone Number", "Enter your phone number", CandidateProfileState.phone, CandidateProfileState.set_phone, "tel"),
                form_field("Location", "e.g. Bangalore, India", CandidateProfileState.location, CandidateProfileState.set_location),
                form_field("Date of Joining", "Select or enter date", CandidateProfileState.date_of_joining, CandidateProfileState.set_date_of_joining, "date"),
                form_select("Employment Status", "Select Status", CandidateProfileState.employment_status_options, CandidateProfileState.employment_status, CandidateProfileState.set_employment_status),
                columns="2",
                spacing="4",
                width="100%",
            ),

            # ── 2. Organization Details Section ────────────────────────
            section_header("Organization Details"),
            rx.grid(
                form_field("Company / Business Unit", "e.g. TVS Motor Company", CandidateProfileState.company_bu, CandidateProfileState.set_company_bu),
                form_select("Department", "Select Department", CandidateProfileState.department_options, CandidateProfileState.department, CandidateProfileState.set_department),
                form_select("Designation", "Select Designation", CandidateProfileState.designation_options, CandidateProfileState.designation, CandidateProfileState.set_designation),
                form_select("Grade / Level", "Select Grade", CandidateProfileState.grade_options, CandidateProfileState.grade_level, CandidateProfileState.set_grade_level),
                form_field("Reporting Manager", "e.g. Ravi Kumar", CandidateProfileState.reporting_manager, CandidateProfileState.set_reporting_manager),
                form_field("Work Location", "e.g. Hosur Plant, Block C", CandidateProfileState.work_location, CandidateProfileState.set_work_location),
                columns="2",
                spacing="4",
                width="100%",
            ),

            # ── Save Button ───────────────────────────────────────────
            rx.hstack(
                rx.spacer(),
                rx.button(
                    "Save Profile",
                    on_click=CandidateProfileState.save_profile,
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                    margin_top="2.5em",
                    size="3",
                    padding_x="2em",
                ),
                width="100%",
            ),

            width="100%",
            max_width="900px",
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="2.5em",
            align_items="stretch",
            spacing="0",
        ),
        width="100%",
        display="flex",
        justify_content="center",
    )


def candidate_profile_page() -> rx.Component:
    return candidate_shell(
        active="profile",
        title="My Profile",
        subtitle="Manage your personal information and organization details.",
        content=profile_page_content(),
    )
