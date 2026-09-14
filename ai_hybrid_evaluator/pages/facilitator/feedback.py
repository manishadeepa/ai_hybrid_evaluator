"""
Facilitator Feedback Page — Global module for managing candidate feedback across assessments.
"""

import reflex as rx
from ai_hybrid_evaluator.components.layout.facilitator_shell import facilitator_shell
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


def feedback_page_content() -> rx.Component:
    """Feedback page allowing facilitator to view candidate performance and provide persistent feedback."""
    perf = FacilitatorState.feedback_candidate_performance
    return rx.vstack(
        # 1. Page Header
        rx.vstack(
            rx.text(
                "Feedback",
                font_family=FONT_DISPLAY,
                size="6",
                weight="bold",
                color="#0F172A",
            ),
            rx.text(
                "Provide and manage feedback for candidates based on their performance.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
            ),
            spacing="1",
            align_items="start",
            width="100%",
        ),

        # 2. Dynamic Dropdowns Row: Assessment -> Test -> Candidate
        rx.hstack(
            # Column 1: Assessment
            rx.vstack(
                rx.text("Assessment", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["slate"]),
                rx.select(
                    FacilitatorState.feedback_assessment_options,
                    value=FacilitatorState.selected_feedback_assessment,
                    on_change=FacilitatorState.set_feedback_assessment,
                    placeholder="Select Assessment...",
                    size="3",
                    width="100%",
                ),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            # Column 2: Test
            rx.vstack(
                rx.text("Test", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["slate"]),
                rx.select(
                    FacilitatorState.feedback_test_options,
                    value=FacilitatorState.selected_feedback_test,
                    on_change=FacilitatorState.set_feedback_test,
                    placeholder="Select Test...",
                    size="3",
                    width="100%",
                ),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            # Column 3: Candidate
            rx.vstack(
                rx.text("Candidate", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["slate"]),
                rx.select(
                    FacilitatorState.feedback_candidate_options,
                    value=FacilitatorState.selected_feedback_candidate,
                    on_change=FacilitatorState.set_feedback_candidate,
                    placeholder="Select Candidate...",
                    size="3",
                    width="100%",
                ),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            spacing="4",
            width="100%",
            align_items="start",
            margin_y="1.6em",
        ),

        # 3. Two Side-by-Side Cards: Candidate Performance + Facilitator Feedback
        rx.hstack(
            # Left Card: Candidate Performance
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.icon("bar-chart-2", size=20, color="#6366F1"),
                        rx.text(
                            "Candidate Performance",
                            font_family=FONT_DISPLAY,
                            size="4",
                            weight="bold",
                            color="#0F172A",
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                    ),

                    # 4 Metric Cards Row
                    rx.grid(
                        # Card 1: Marks Obtained
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("award", size=16, color="#7C3AED"),
                                    rx.text("Marks Obtained", font_family=FONT_BODY, size="1", color="#64748B", weight="medium"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                rx.text(
                                    perf["marks_obtained"],
                                    font_family=FONT_DISPLAY,
                                    size="6",
                                    weight="bold",
                                    color="#0F172A",
                                ),
                                spacing="2",
                                align_items="center",
                                justify="center",
                                width="100%",
                            ),
                            background="#F5F3FF",
                            border="1px solid #EDE9FE",
                            border_radius="10px",
                            padding="1.1em 0.8em",
                            width="100%",
                        ),

                        # Card 2: Normalized Score
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("percent", size=16, color="#2563EB"),
                                    rx.text("Normalized Score", font_family=FONT_BODY, size="1", color="#64748B", weight="medium"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                rx.text(
                                    perf["normalized_score"],
                                    font_family=FONT_DISPLAY,
                                    size="6",
                                    weight="bold",
                                    color="#0F172A",
                                ),
                                spacing="2",
                                align_items="center",
                                justify="center",
                                width="100%",
                            ),
                            background="#EFF6FF",
                            border="1px solid #DBEAFE",
                            border_radius="10px",
                            padding="1.1em 0.8em",
                            width="100%",
                        ),

                        # Card 3: Status
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("circle-check", size=18, color="#10B981"),
                                    rx.text("Status", font_family=FONT_BODY, size="1", color="#64748B", weight="medium"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                rx.box(
                                    rx.cond(
                                        perf["status"] == "Passed",
                                        rx.box(rx.text("Passed", font_family=FONT_BODY, size="2", weight="bold", color="#03543F"), background="#DEF7EC", border_radius="12px", padding="0.25em 1em", display="inline-flex"),
                                        rx.cond(
                                            perf["status"] == "Failed",
                                            rx.box(rx.text("Failed", font_family=FONT_BODY, size="2", weight="bold", color="#9B1C1C"), background="#FDE8E8", border_radius="12px", padding="0.25em 1em", display="inline-flex"),
                                            rx.box(rx.text("Pending", font_family=FONT_BODY, size="2", weight="bold", color="#854D0E"), background="#FEF08A", border_radius="12px", padding="0.25em 1em", display="inline-flex"),
                                        ),
                                    ),
                                    margin_top="0.2em",
                                ),
                                spacing="2",
                                align_items="center",
                                justify="center",
                                width="100%",
                            ),
                            background="#ECFDF5",
                            border="1px solid #D1FAE5",
                            border_radius="10px",
                            padding="1.1em 0.8em",
                            width="100%",
                        ),
                        columns="3",
                        spacing="3",
                        width="100%",
                        margin_y="1.2em",
                    ),

                    # Bottom Subcard: Test Details
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "Test Details",
                                font_family=FONT_BODY,
                                size="2",
                                weight="bold",
                                color="#475467",
                                margin_bottom="0.4em",
                            ),
                            rx.hstack(
                                # Left Details Column
                                rx.vstack(
                                    rx.hstack(
                                        rx.text("Test Type", width="85px", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(":", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(perf["test_type"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium"),
                                        spacing="2",
                                        align_items="center",
                                    ),
                                    rx.hstack(
                                        rx.text("Test Date", width="85px", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(":", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(perf["test_date"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium"),
                                        spacing="2",
                                        align_items="center",
                                    ),
                                    spacing="2",
                                    flex="1",
                                    align_items="start",
                                ),
                                # Right Details Column
                                rx.vstack(
                                    rx.hstack(
                                        rx.text("Weightage", width="105px", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(":", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(perf["weightage"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium"),
                                        spacing="2",
                                        align_items="center",
                                    ),
                                    rx.hstack(
                                        rx.text("Maximum Marks", width="105px", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(":", font_family=FONT_BODY, size="2", color="#64748B"),
                                        rx.text(perf["max_marks"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium"),
                                        spacing="2",
                                        align_items="center",
                                    ),
                                    spacing="2",
                                    flex="1",
                                    align_items="start",
                                ),
                                width="100%",
                                align_items="start",
                            ),
                            spacing="1",
                            align_items="start",
                            width="100%",
                        ),
                        background="#F8FAFC",
                        border="1px solid #E2E8F0",
                        border_radius="10px",
                        padding="1.2em 1.4em",
                        width="100%",
                    ),

                    spacing="0",
                    align_items="stretch",
                    width="100%",
                ),
                background="white",
                border="1px solid #E2E8F0",
                border_radius="14px",
                padding="1.4em 1.6em",
                flex="1",
                box_shadow="0 1px 3px rgba(0,0,0,0.03)",
            ),

            # Right Card: Facilitator Feedback
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.icon("message-square", size=20, color="#6366F1"),
                        rx.text(
                            "Facilitator Feedback",
                            font_family=FONT_DISPLAY,
                            size="4",
                            weight="bold",
                            color="#0F172A",
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                    ),
                    rx.text(
                        "Provide feedback on the candidate's performance, including strengths, areas for improvement, and suggestions.",
                        font_family=FONT_BODY,
                        size="2",
                        color="#64748B",
                        margin_top="0.4em",
                        margin_bottom="0.8em",
                    ),

                    # Textarea
                    rx.text_area(
                        value=FacilitatorState.facilitator_feedback_text,
                        on_change=FacilitatorState.set_facilitator_feedback_text,
                        placeholder="Enter your feedback here...",
                        rows="5",
                        max_length=1000,
                        width="100%",
                        font_family=FONT_BODY,
                        size="2",
                        border_radius="8px",
                        border="1px solid #CBD5E1",
                        background="white",
                    ),

                    # Character counter
                    rx.hstack(
                        rx.spacer(),
                        rx.text(
                            "Characters: ",
                            FacilitatorState.feedback_character_count,
                            " / 1000",
                            font_family=FONT_BODY,
                            size="1",
                            color="#64748B",
                        ),
                        width="100%",
                        margin_top="0.3em",
                        margin_bottom="1em",
                    ),

                    # Feedback Guidelines box
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("lightbulb", size=16, color="#7C3AED"),
                                rx.text(
                                    "Feedback Guidelines",
                                    font_family=FONT_BODY,
                                    size="2",
                                    weight="bold",
                                    color="#5B21B6",
                                ),
                                spacing="2",
                                align_items="center",
                            ),
                            rx.vstack(
                                rx.text("•  Highlight the candidate's strengths.", font_family=FONT_BODY, size="2", color="#6D28D9"),
                                rx.text("•  Mention specific areas for improvement.", font_family=FONT_BODY, size="2", color="#6D28D9"),
                                rx.text("•  Provide constructive and actionable suggestions.", font_family=FONT_BODY, size="2", color="#6D28D9"),
                                spacing="1",
                                align_items="start",
                                padding_left="0.4em",
                            ),
                            spacing="2",
                            align_items="start",
                            width="100%",
                        ),
                        background="#F5F3FF",
                        border="1px solid #DDD6FE",
                        border_radius="10px",
                        padding="1em 1.2em",
                        width="100%",
                        margin_bottom="1.4em",
                    ),

                    # Action buttons
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            rx.icon("rotate-ccw", size=14),
                            "Reset",
                            on_click=FacilitatorState.reset_feedback_form,
                            size="2",
                            variant="outline",
                            color="#334155",
                            border="1px solid #CBD5E1",
                            background="white",
                            font_family=FONT_BODY,
                            weight="medium",
                            border_radius="8px",
                            cursor="pointer",
                            _hover={"background": "#F8FAFC"},
                            padding_x="1.2em",
                        ),
                        rx.button(
                            rx.icon("save", size=14),
                            "Save Feedback",
                            on_click=FacilitatorState.save_facilitator_feedback,
                            size="2",
                            background="#4F46E5",
                            color="white",
                            font_family=FONT_BODY,
                            weight="medium",
                            border_radius="8px",
                            cursor="pointer",
                            _hover={"background": "#4338CA"},
                            box_shadow="0 1px 3px rgba(79, 70, 229, 0.25)",
                            padding_x="1.2em",
                        ),
                        spacing="3",
                        align_items="center",
                        width="100%",
                    ),

                    spacing="0",
                    align_items="stretch",
                    width="100%",
                ),
                background="white",
                border="1px solid #E2E8F0",
                border_radius="14px",
                padding="1.4em 1.6em",
                flex="1",
                box_shadow="0 1px 3px rgba(0,0,0,0.03)",
            ),
            spacing="5",
            width="100%",
            align_items="start",
        ),
        spacing="0",
        width="100%",
        align_items="stretch",
    )


def facilitator_feedback_page() -> rx.Component:
    return facilitator_shell(
        active="feedback",
        title="Feedback",
        subtitle="Provide and manage feedback for candidates based on their performance.",
        content=feedback_page_content(),
    )
