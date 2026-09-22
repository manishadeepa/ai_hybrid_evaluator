"""Admin Assessment Reports page — displaying the Facilitator Results page UI."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import (
    _results_all_average_scores_row,
    _results_all_candidates_table_card,
    _results_analysis_test_selector,
    _results_control_bar,
    _results_download_pdf_modal,
    _results_individual_scores_row,
    _results_report_modal,
    _results_top_header,
    results_performance_analysis_card,
)
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


class AdminReportsPageState(rx.State):
    """Handles assessment selection and state synchronization for Admin Reports."""

    @rx.var
    async def assessment_options(self) -> list[str]:
        admin_state = await self.get_state(AdminState)
        return [a["name"] for a in admin_state.assessments if "name" in a]

    async def select_assessment(self, name: str):
        if not name:
            return
        admin_state = await self.get_state(AdminState)
        fac_state = await self.get_state(FacilitatorState)
        for i, a in enumerate(admin_state.assessments):
            if a.get("name") == name:
                fac_state.selected_assessment_index = i
                fac_state.selected_assessment_name = name
                tests = a.get("tests", [])
                final_test = a.get("final_test", "")
                fac_state.selected_assessment_final_test = final_test
                all_t = list(tests) + ([final_test] if final_test else [])
                fac_state.selected_test_name = all_t[0] if all_t else ""
                fac_state.selected_evaluation_test = fac_state.selected_test_name
                fac_state._current_assessment_candidates = [
                    {"name": c["name"], "emp_id": c["emp_id"]}
                    for c in admin_state.candidates
                    if c["emp_id"] in a.get("assigned_candidates", [])
                ]
                await fac_state.sync_assessment_weightage(name)
                break

    async def on_load(self):
        admin_state = await self.get_state(AdminState)
        fac_state = await self.get_state(FacilitatorState)
        target = fac_state.selected_assessment_name
        names = [a["name"] for a in admin_state.assessments if "name" in a]
        if not target or target not in names:
            if names:
                await self.select_assessment(names[0])
        else:
            await self.select_assessment(target)


def _admin_reports_assessment_bar() -> rx.Component:
    """Assessment selector bar allowing the Admin to switch between assessments."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("layers", size=16, color=COLORS["primary"]),
                rx.text(
                    "Assessment:",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
            ),
            rx.select(
                AdminReportsPageState.assessment_options,
                value=FacilitatorState.selected_assessment_name,
                on_change=AdminReportsPageState.select_assessment,
                size="2",
                variant="surface",
                min_width="220px",
            ),
            rx.spacer(),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="0.8em 1.2em",
        width="100%",
    )


def reports_page() -> rx.Component:
    """Admin Reports page displaying the exact Facilitator Results page UI."""
    content = rx.vstack(
        # Assessment selector bar for Admin
        _admin_reports_assessment_bar(),

        # Top assessment header + action buttons (Results title, name, Download PDF)
        _results_top_header(),

        # View mode toggle (Individual Candidate vs All Candidates) + Filters
        _results_control_bar(),

        # Content based on View Mode
        rx.cond(
            FacilitatorState.results_view_mode == "individual",
            # ── 1. INDIVIDUAL CANDIDATE VIEW ────────────────────────────────
            rx.vstack(
                # Dynamic test scores row + Overall Score card
                _results_individual_scores_row(),

                # Test selector — applies to Performance Analysis below
                _results_analysis_test_selector(),

                # Performance Analysis (Tabs: Overall, CO, LO, Knowledge Type, Domain, RBT Level, Question-wise)
                results_performance_analysis_card(),

                spacing="4",
                width="100%",
                align_items="stretch",
            ),

            # ── 2. ALL CANDIDATES VIEW ──────────────────────────────────────
            rx.vstack(
                # Average scores row across all tests + Overall Average card
                _results_all_average_scores_row(),

                # Candidate Performance table with dynamic test columns & search
                _results_all_candidates_table_card(),

                # Test selector — applies to Performance Analysis below
                _results_analysis_test_selector(),

                # Performance Analysis card for cohort
                results_performance_analysis_card(),

                spacing="4",
                width="100%",
                align_items="stretch",
            ),
        ),

        # Embedded Report Modal
        _results_report_modal(),

        # Results Download PDF Modal Dialog
        _results_download_pdf_modal(),

        spacing="4",
        width="100%",
        align_items="stretch",
        on_mount=AdminReportsPageState.on_load,
    )

    return admin_shell(
        active="reports",
        title="Assessment Reports",
        subtitle="View overall assessment reports generated by facilitators after completion of assessments.",
        content=content,
    )