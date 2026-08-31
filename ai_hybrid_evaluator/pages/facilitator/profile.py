"""Facilitator Profile Page."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorProfileState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY

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
            rx.hstack(
                rx.avatar(src=FacilitatorProfileState.profile_photo_url, size="7", radius="full"),
                rx.vstack(
                    rx.text("Profile Photo", font_family=FONT_BODY, size="3", weight="bold"),
                    rx.button(
                        "Upload Photo",
                        rx.icon("upload", size=14),
                        on_click=FacilitatorProfileState.simulate_upload_photo,
                        variant="outline",
                        color=COLORS["primary"],
                        border=f"1px solid {COLORS['primary']}",
                        _hover={"background": COLORS["canvas"]},
                    ),
                    align_items="start",
                    spacing="2",
                ),
                spacing="4",
                align_items="center",
                margin_bottom="2em",
            ),
            
            section_header("Basic Information"),
            rx.grid(
                form_field("Full Name", "Enter your full name", FacilitatorProfileState.full_name, FacilitatorProfileState.set_full_name),
                form_field("Email", "Enter your email", FacilitatorProfileState.email, FacilitatorProfileState.set_email, "email"),
                form_field("Phone", "Enter your phone number", FacilitatorProfileState.phone, FacilitatorProfileState.set_phone, "tel"),
                form_field("Location", "Enter your location", FacilitatorProfileState.location, FacilitatorProfileState.set_location),
                columns="2",
                spacing="4",
                width="100%",
            ),

            section_header("Professional Details"),
            rx.grid(
                form_select("Designation", "Select Designation", ["Junior Evaluator", "Senior Evaluator", "Lead Evaluator", "External Consultant"], FacilitatorProfileState.designation, FacilitatorProfileState.set_designation),
                form_select(
                    "Department / Function", 
                    "Select Department", 
                    [
                        "Research & Development (R&D)", 
                        "Manufacturing & Production", 
                        "Quality Assurance", 
                        "Supply Chain & Operations", 
                        "Sales & Marketing", 
                        "Human Resources", 
                        "Learning & Development", 
                        "IT & Digital Transformation", 
                        "Other"
                    ], 
                    FacilitatorProfileState.department, 
                    FacilitatorProfileState.set_department
                ),
                form_field("Business Unit", "e.g. HR", FacilitatorProfileState.business_unit, FacilitatorProfileState.set_business_unit),
                form_field("Years of Experience", "e.g. 5", FacilitatorProfileState.years_experience, FacilitatorProfileState.set_years_experience, "number"),
                columns="2",
                spacing="4",
                width="100%",
            ),

            section_header("Expertise"),
            rx.grid(
                form_select("Primary Area of Expertise", "Select Area", ["Technical Interviews", "Behavioral Assessments", "Language Proficiency", "Domain Specific"], FacilitatorProfileState.primary_expertise, FacilitatorProfileState.set_primary_expertise),
                form_field("Specific Skills / Expertise", "e.g. Python, System Design", FacilitatorProfileState.specific_skills, FacilitatorProfileState.set_specific_skills),
                columns="2",
                spacing="4",
                width="100%",
            ),

            section_header("Education"),
            rx.grid(
                form_select("Highest Qualification", "Select Qualification", ["Bachelor's Degree", "Master's Degree", "PhD", "Diploma", "Other"], FacilitatorProfileState.highest_qualification, FacilitatorProfileState.set_highest_qualification),
                form_select(
                    "Specialization", 
                    "Select Specialization", 
                    [
                        "Mechanical Engineering", 
                        "Electrical and Electronics", 
                        "Automobile Engineering", 
                        "Mechanical & Automation", 
                        "Electronics and Communication Engineering", 
                        "Computer Science",
                        "Other"
                    ], 
                    FacilitatorProfileState.specialization, 
                    FacilitatorProfileState.set_specialization
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),

            section_header("Experience & Domains"),
            rx.grid(
                form_select("Training Experience", "Select Experience Level", ["0-2 years", "3-5 years", "6-10 years", "10+ years"], FacilitatorProfileState.training_experience, FacilitatorProfileState.set_training_experience),
                form_select(
                    "Subjects / Domains", 
                    "Select Domain", 
                    [
                        "Two-Wheeler Manufacturing", 
                        "Electric Vehicles (EV) & Battery Tech", 
                        "Engine R&D", 
                        "Vehicle Dynamics & Design",
                        "Quality Assurance & Testing", 
                        "IT & Software Development", 
                        "Automotive Automation",
                        "Other"
                    ], 
                    FacilitatorProfileState.subjects_domains, 
                    FacilitatorProfileState.set_subjects_domains
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),

            section_header("Availability"),
            form_field("Availability", "e.g. Weekdays 9 AM - 5 PM EST", FacilitatorProfileState.availability, FacilitatorProfileState.set_availability),

            rx.hstack(
                rx.spacer(),
                rx.button(
                    "Save Profile",
                    on_click=FacilitatorProfileState.save_profile,
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    _hover={"background": COLORS["primary_hover"]},
                    margin_top="2em",
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

def facilitator_profile_page() -> rx.Component:
    return facilitator_shell(
        active="profile",
        title="My Profile",
        subtitle="Manage your personal information and professional details.",
        content=profile_page_content(),
    )
