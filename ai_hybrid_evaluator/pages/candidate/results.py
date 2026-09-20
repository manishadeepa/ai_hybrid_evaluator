"""Candidate Results page — read-only view of candidate's own finalized results and performance analysis."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.candidate_shell import candidate_shell
from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import (
    results_vertical_dimension_bar_item,
)
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.candidate_state import CandidateState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


class CandidateResultsState(rx.State):
    """State for Candidate Results page.

    Provides a clean, read-only integration point for finalized evaluation results.
    """

    selected_assessment_name: str = ""
    selected_test_name: str = ""
    active_tab: str = "co"  # "co", "lo", "knowledge_type", "domain", "rbt_level", "question_wise"

    def set_selected_assessment(self, name: str):
        self.selected_assessment_name = name
        self.selected_test_name = ""

    def select_test(self, test_name: str):
        self.selected_test_name = test_name
        self.active_tab = "co"

    def clear_selected_test(self):
        self.selected_test_name = ""

    def set_active_tab(self, tab: str):
        self.active_tab = tab

    async def on_load(self):
        opts = await self.assessment_options
        if not self.selected_assessment_name and opts:
            self.selected_assessment_name = opts[0]

    # ─────────────────────────────────────────────────────────────────────────
    # FUTURE BACKEND RESULT-DATA INTEGRATION POINT
    # ─────────────────────────────────────────────────────────────────────────
    # This method is the centralized frontend integration point where finalized
    # candidate evaluation data is retrieved.
    #
    # Flow:
    #   Facilitator evaluates candidate
    #   → Facilitator Results contains finalized result
    #   → Backend stores/provides finalized result
    #   → Candidate Results loads that candidate's result
    #   → Candidate sees only their own data
    #
    # When backend APIs/database endpoints are connected, replace or augment this
    # lookup with the corresponding backend fetch call.
    # ─────────────────────────────────────────────────────────────────────────
    async def _fetch_finalized_test_result(self, cand_id: str, assessment_name: str, test_name: str) -> dict:
        if not assessment_name or not test_name:
            return {}
        try:
            fac_st = await self.get_state(FacilitatorState)
            results = fac_st.real_ai_results_per_candidate
        except Exception:
            return {}

        target_test = test_name.strip().lower()
        target_cand = cand_id.strip().lower()

        for key, res in results.items():
            parts = key.split(":")
            cand_part = parts[0].strip()
            test_part = parts[1].strip() if len(parts) > 1 else ""

            part_id = cand_part.split("(")[-1].rstrip(")").strip() if "(" in cand_part else cand_part

            if test_part.lower() == target_test:
                if (target_cand and target_cand == part_id.lower()) or (target_cand in cand_part.lower()):
                    return res
        return {}

    @rx.var
    async def assessment_options(self) -> list[str]:
        """Assessments assigned to the logged-in candidate."""
        auth_st = await self.get_state(AuthState)
        admin_st = await self.get_state(AdminState)
        cand_id = auth_st.candidate_emp_id or "CAND-2031"

        options = []
        for a in admin_st.assessments:
            assigned = a.get("assigned_candidates", [])
            if not assigned or cand_id in assigned:
                name = a.get("name", "")
                if name and name not in options:
                    options.append(name)
        if not options and admin_st.assessments:
            options = [a.get("name", "") for a in admin_st.assessments if a.get("name")]
        return options

    @rx.var
    async def current_assessment_name(self) -> str:
        if self.selected_assessment_name:
            return self.selected_assessment_name
        opts = await self.assessment_options
        return opts[0] if opts else "Quality"

    @rx.var
    async def tests_table_rows(self) -> list[dict]:
        """Table data for 'Tests in this Assessment'."""
        auth_st = await self.get_state(AuthState)
        admin_st = await self.get_state(AdminState)
        cand_st = await self.get_state(CandidateState)
        cand_id = auth_st.candidate_emp_id or "CAND-2031"
        asmn = await self.current_assessment_name

        target_a = next((a for a in admin_st.assessments if a.get("name") == asmn), None)
        if not target_a:
            return []

        all_tests = list(target_a.get("tests", []))
        final_test = target_a.get("final_test", "")
        if final_test and final_test not in all_tests:
            all_tests.append(final_test)

        submitted_map = cand_st.submitted_tests.get(asmn, [])

        rows = []
        for i, t_name in enumerate(all_tests, 1):
            eval_data = await self._fetch_finalized_test_result(cand_id, asmn, t_name)
            is_submitted = (t_name in submitted_map) or bool(eval_data)

            if eval_data:
                pct = eval_data.get("percentage", "—")
                if pct != "—" and not str(pct).endswith("%"):
                    pct = f"{pct}%"
                sub_date = eval_data.get("submission_date") or eval_data.get("submitted_on") or "2026-09-10"
                eval_date = eval_data.get("eval_date") or eval_data.get("evaluated_on") or "2026-09-12"

                rows.append({
                    "idx": str(i),
                    "name": t_name,
                    "status": "Evaluated",
                    "status_color": "green",
                    "score": str(pct),
                    "submitted_on": str(sub_date),
                    "evaluated_on": str(eval_date),
                    "is_evaluated": True,
                })
            elif is_submitted:
                rows.append({
                    "idx": str(i),
                    "name": t_name,
                    "status": "Submitted",
                    "status_color": "indigo",
                    "score": "—",
                    "submitted_on": "2026-09-15",
                    "evaluated_on": "—",
                    "is_evaluated": False,
                })
            else:
                rows.append({
                    "idx": str(i),
                    "name": t_name,
                    "status": "Not Submitted",
                    "status_color": "amber",
                    "score": "—",
                    "submitted_on": "—",
                    "evaluated_on": "—",
                    "is_evaluated": False,
                })
        return rows

    @rx.var
    async def selected_test_eval_data(self) -> dict:
        """Fetch finalized evaluation data for currently selected test."""
        if not self.selected_test_name:
            return {}
        auth_st = await self.get_state(AuthState)
        cand_id = auth_st.candidate_emp_id or "CAND-2031"
        asmn = await self.current_assessment_name
        return await self._fetch_finalized_test_result(cand_id, asmn, self.selected_test_name)

    @rx.var
    async def has_evaluated_selection(self) -> bool:
        return bool(await self.selected_test_eval_data)

    @rx.var
    async def test_score_display(self) -> str:
        d = await self.selected_test_eval_data
        pct = d.get("percentage", "—")
        if pct != "—" and not str(pct).endswith("%"):
            return f"{pct}%"
        return str(pct)

    @rx.var
    async def test_marks_display(self) -> str:
        d = await self.selected_test_eval_data
        score = d.get("score", "—")
        max_s = d.get("max_score", "—")
        if score != "—" and max_s != "—":
            return f"{score} / {max_s} marks"
        return "—"

    @rx.var
    async def test_result_status(self) -> str:
        d = await self.selected_test_eval_data
        pct_raw = str(d.get("percentage", "0")).replace("%", "").strip()
        try:
            val = float(pct_raw)
            return "Pass" if val >= 50.0 else "Fail"
        except Exception:
            return "Pass" if d else "—"

    @rx.var
    async def test_result_subtext(self) -> str:
        st = await self.test_result_status
        return "Good performance!" if st == "Pass" else "Needs Improvement"

    @rx.var
    async def test_total_questions(self) -> str:
        d = await self.selected_test_eval_data
        qs = d.get("questions", [])
        return str(len(qs)) if qs else "10"

    @rx.var
    async def test_attempted_questions(self) -> str:
        d = await self.selected_test_eval_data
        qs = d.get("questions", [])
        return f"{len(qs)} attempted" if qs else "10 attempted"

    @rx.var
    async def test_time_taken(self) -> str:
        d = await self.selected_test_eval_data
        return str(d.get("time_taken", "28m 15s"))

    @rx.var
    async def test_total_time(self) -> str:
        return "of 60 minutes"

    @rx.var
    async def test_submitted_on_display(self) -> str:
        d = await self.selected_test_eval_data
        return str(d.get("submission_date") or d.get("submitted_on") or "2026-09-10")

    @rx.var
    async def test_evaluated_on_display(self) -> str:
        d = await self.selected_test_eval_data
        return str(d.get("eval_date") or d.get("evaluated_on") or "2026-09-12")

    @rx.var
    async def chart_items_co(self) -> list[dict]:
        d = await self.selected_test_eval_data
        items = d.get("co", [])
        return [{"name": item.get("name", f"CO{i+1}"), "score": int(item.get("score", 0))} for i, item in enumerate(items)]

    @rx.var
    async def chart_items_lo(self) -> list[dict]:
        d = await self.selected_test_eval_data
        items = d.get("lo", [])
        return [{"name": item.get("name", f"LO{i+1}"), "score": int(item.get("score", 0))} for i, item in enumerate(items)]

    @rx.var
    async def chart_items_kt(self) -> list[dict]:
        d = await self.selected_test_eval_data
        items = d.get("knowledge_type", [])
        return [{"name": item.get("name", "KT"), "score": int(item.get("score", 0))} for item in items]

    @rx.var
    async def chart_items_domain(self) -> list[dict]:
        d = await self.selected_test_eval_data
        items = d.get("domain", [])
        return [{"name": item.get("name", "Domain"), "score": int(item.get("score", 0))} for item in items]

    @rx.var
    async def chart_items_rbt(self) -> list[dict]:
        d = await self.selected_test_eval_data
        items = d.get("rbt_level", [])
        return [{"name": item.get("name", "RBT"), "score": int(item.get("score", 0))} for item in items]

    @rx.var
    async def chart_items_test_wise(self) -> list[dict]:
        d = await self.selected_test_eval_data
        pct_raw = str(d.get("percentage", "0")).replace("%", "").strip()
        try:
            score = int(float(pct_raw))
        except Exception:
            score = 0
        return [{"name": self.selected_test_name or "Test", "score": score}]

    @rx.var
    async def question_items(self) -> list[dict]:
        d = await self.selected_test_eval_data
        qs = d.get("questions", [])
        res = []
        for i, q in enumerate(qs, 1):
            obt = q.get("marks_obtained") or q.get("ai_score") or q.get("marks") or 0
            mx = q.get("max_marks", 5)
            q_text = q.get("question") or q.get("question_text") or f"Question {i}"
            c_ans = q.get("candidate_answer") or q.get("answer") or q.get("user_answer") or "—"
            corr_ans = q.get("correct_answer") or q.get("ideal_answer") or "—"
            try:
                obt_f = float(obt)
                mx_f = float(mx)
                if obt_f >= mx_f:
                    status = "Correct"
                    status_color = "green"
                elif obt_f > 0:
                    status = "Partially Correct"
                    status_color = "amber"
                else:
                    status = "Incorrect"
                    status_color = "red"
            except Exception:
                status = "Correct"
                status_color = "green"

            res.append({
                "idx": str(i),
                "question": str(q_text),
                "co": str(q.get("co", f"CO{((i-1)%4)+1}")),
                "lo": str(q.get("lo", f"LO{((i-1)%4)+1}")),
                "knowledge_type": str(q.get("knowledge_type", "Conceptual")),
                "domain": str(q.get("domain", "Engineering")),
                "rbt_level": str(q.get("rbt_level", "Understand")),
                "candidate_answer": str(c_ans),
                "correct_answer": str(corr_ans),
                "marks": f"{obt} / {mx}",
                "status": status,
                "status_color": status_color,
            })
        return res


# ─────────────────────────────────────────────────────────────────────────────
# 1. Page Header Card
# ─────────────────────────────────────────────────────────────────────────────

def _results_page_header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.box(
                    rx.icon("bar-chart-2", size=22, color="#6366F1"),
                    background="#EEF2FF",
                    padding="0.65em",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(
                        "My Results",
                        font_family=FONT_DISPLAY,
                        size="5",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "View your test results and performance analytics across completed assessments.",
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
            rx.vstack(
                rx.text("Select Assessment", font_family=FONT_BODY, size="1", weight="medium", color=COLORS["slate"]),
                rx.select(
                    CandidateResultsState.assessment_options,
                    value=CandidateResultsState.current_assessment_name,
                    on_change=CandidateResultsState.set_selected_assessment,
                    size="2",
                    variant="surface",
                    min_width="220px",
                ),
                spacing="1",
                align_items="start",
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em 1.5em",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Tests in this Assessment Card
# ─────────────────────────────────────────────────────────────────────────────

def _tests_in_assessment_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=18, color="#6366F1"),
                    background="#EEF2FF",
                    padding="0.5em",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text(
                        "Tests in this Assessment",
                        font_family=FONT_BODY,
                        size="3",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "View the status and results of all tests in this assessment.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                padding_bottom="0.8em",
            ),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("#", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="50px"),
                            rx.table.column_header_cell(rx.text("Test Name", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]), min_width="160px"),
                            rx.table.column_header_cell(rx.text("Status", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="130px"),
                            rx.table.column_header_cell(rx.text("Score", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="100px"),
                            rx.table.column_header_cell(rx.text("Submitted On", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="140px"),
                            rx.table.column_header_cell(rx.text("Evaluated On", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="140px"),
                            rx.table.column_header_cell(rx.text("Action", font_family=FONT_BODY, size="2", weight="bold", color=COLORS["slate"]), width="130px"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            CandidateResultsState.tests_table_rows,
                            lambda row: rx.table.row(
                                rx.table.cell(rx.text(row["idx"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(row["name"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(
                                    rx.badge(
                                        row["status"],
                                        color_scheme=row["status_color"],
                                        variant="soft",
                                        size="2",
                                    ),
                                ),
                                rx.table.cell(rx.text(row["score"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(rx.text(row["submitted_on"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(row["evaluated_on"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(
                                    rx.cond(
                                        row["is_evaluated"],
                                        rx.button(
                                            rx.icon("eye", size=14),
                                            "View Result",
                                            size="1",
                                            background="#6366F1",
                                            color="white",
                                            font_family=FONT_BODY,
                                            weight="medium",
                                            border_radius="6px",
                                            cursor="pointer",
                                            _hover={"background": "#4F46E5"},
                                            on_click=CandidateResultsState.select_test(row["name"]),
                                        ),
                                        rx.cond(
                                            row["status"] == "Submitted",
                                            rx.button(
                                                rx.icon("clock", size=14),
                                                "Result Pending",
                                                size="1",
                                                variant="soft",
                                                color_scheme="gray",
                                                font_family=FONT_BODY,
                                                cursor="not-allowed",
                                                disabled=True,
                                            ),
                                            rx.button(
                                                rx.icon("play", size=14),
                                                "Start Test",
                                                size="1",
                                                variant="soft",
                                                color_scheme="gray",
                                                font_family=FONT_BODY,
                                                cursor="not-allowed",
                                                disabled=True,
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                width="100%",
                overflow_x="auto",
            ),
            spacing="0",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Selected Test Header & Metric Cards
# ─────────────────────────────────────────────────────────────────────────────

def _test_detail_header() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.icon_button(
                rx.icon("arrow-left", size=18),
                variant="soft",
                color_scheme="gray",
                size="2",
                cursor="pointer",
                on_click=CandidateResultsState.clear_selected_test,
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        CandidateResultsState.selected_test_name + " - Result and Performance Analysis",
                        font_family=FONT_DISPLAY,
                        size="5",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.badge("Evaluated", color_scheme="green", variant="soft", size="1"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Detailed performance analysis for " + CandidateResultsState.selected_test_name + " test.",
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
        rx.hstack(
            rx.hstack(
                rx.icon("calendar", size=14, color="#7C3AED"),
                rx.vstack(
                    rx.text("Submitted On", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(CandidateResultsState.test_submitted_on_display, font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"]),
                    spacing="0",
                    align_items="start",
                ),
                padding="0.4em 0.8em",
                border=f"1px solid {COLORS['line']}",
                border_radius="8px",
                background="#FDFCFF",
                spacing="2",
                align_items="center",
            ),
            rx.hstack(
                rx.icon("calendar-check", size=14, color="#2563EB"),
                rx.vstack(
                    rx.text("Evaluated On", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(CandidateResultsState.test_evaluated_on_display, font_family=FONT_BODY, size="1", weight="bold", color=COLORS["ink"]),
                    spacing="0",
                    align_items="start",
                ),
                padding="0.4em 0.8em",
                border=f"1px solid {COLORS['line']}",
                border_radius="8px",
                background="#F8FAFC",
                spacing="2",
                align_items="center",
            ),
            spacing="2",
            align_items="center",
        ),
        width="100%",
        align_items="center",
        padding_bottom="0.5em",
    )


def _metric_cards_row() -> rx.Component:
    return rx.grid(
        # Score Card
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("trophy", size=20, color="#D97706"),
                    background="#FEF3C7",
                    padding="0.55em",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Score", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(CandidateResultsState.test_score_display, font_family=FONT_DISPLAY, size="7", weight="bold", color=COLORS["ink"]),
                    rx.text(CandidateResultsState.test_marks_display, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.1em 1.3em",
        ),
        # Result Card
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("circle-check", size=20, color="#059669"),
                    background="#D1FAE5",
                    padding="0.55em",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Result", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(
                        CandidateResultsState.test_result_status,
                        font_family=FONT_DISPLAY,
                        size="7",
                        weight="bold",
                        color=rx.cond(CandidateResultsState.test_result_status == "Pass", "#059669", "#DC2626"),
                    ),
                    rx.text(CandidateResultsState.test_result_subtext, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.1em 1.3em",
        ),
        # Total Questions Card
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("file-text", size=20, color="#2563EB"),
                    background="#DBEAFE",
                    padding="0.55em",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Total Questions", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(CandidateResultsState.test_total_questions, font_family=FONT_DISPLAY, size="7", weight="bold", color=COLORS["ink"]),
                    rx.text(CandidateResultsState.test_attempted_questions, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.1em 1.3em",
        ),
        # Time Taken Card
        rx.box(
            rx.hstack(
                rx.box(
                    rx.icon("clock", size=20, color="#7C3AED"),
                    background="#EDE9FE",
                    padding="0.55em",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Time Taken", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    rx.text(CandidateResultsState.test_time_taken, font_family=FONT_DISPLAY, size="7", weight="bold", color=COLORS["ink"]),
                    rx.text(CandidateResultsState.test_total_time, font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="12px",
            padding="1.1em 1.3em",
        ),
        columns="4",
        spacing="3",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Bar Chart Component (Reusing Facilitator Bar Item & Canvas Layout)
# ─────────────────────────────────────────────────────────────────────────────

def candidate_dimension_bar_chart(items: rx.Var, chart_title: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    chart_title,
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
                # Canvas Box
                rx.box(
                    rx.box(position="absolute", left="0", right="0", top="0%", border_top="1px dashed #E2E8F0", z_index="1"),
                    rx.box(position="absolute", left="0", right="0", top="25%", border_top="1px dashed #E2E8F0", z_index="1"),
                    rx.box(position="absolute", left="0", right="0", top="50%", border_top="1px dashed #E2E8F0", z_index="1"),
                    rx.box(position="absolute", left="0", right="0", top="75%", border_top="1px dashed #E2E8F0", z_index="1"),
                    rx.box(position="absolute", left="0", right="0", bottom="0", border_top="1px solid #CBD5E1", z_index="1"),

                    # Dynamic Pass Mark Line + Badge
                    rx.box(position="absolute", left="0", right="0", top="50%", border_top="1.5px dashed #EF4444", z_index="2"),
                    rx.box(
                        rx.text("Pass Mark", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                        rx.text("50%", font_family=FONT_BODY, size="1", weight="bold", color="#DC2626", text_align="center"),
                        background="#FEF2F2",
                        border="1px solid #FECACA",
                        border_radius="4px",
                        padding="0.15em 0.45em",
                        position="absolute",
                        right="-74px",
                        top="calc(50% - 14px)",
                        z_index="3",
                    ),

                    # Vertical Bars
                    rx.cond(
                        items.length() > 0,
                        rx.hstack(
                            rx.foreach(
                                items,
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
                            rx.text("No data available for this dimension.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
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
                    margin_bottom="32px",
                ),
                spacing="1",
                align_items="start",
                width="100%",
                padding_right="80px",
            ),
            spacing="0",
            width="100%",
            align_items="stretch",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em",
        width="100%",
    )


def _overall_charts_row() -> rx.Component:
    return rx.grid(
        candidate_dimension_bar_chart(CandidateResultsState.chart_items_test_wise, "Test-wise Performance"),
        candidate_dimension_bar_chart(CandidateResultsState.chart_items_rbt, "Performance by Bloom's Taxonomy (RBT Level)"),
        candidate_dimension_bar_chart(CandidateResultsState.chart_items_kt, "Performance by Knowledge Type"),
        columns="3",
        spacing="3",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Question-wise Performance Table
# ─────────────────────────────────────────────────────────────────────────────

def _question_wise_table() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=18, color=COLORS["primary"]),
                rx.text(
                    "Question-wise Performance",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=COLORS["ink"],
                ),
                spacing="2",
                align_items="center",
                padding_bottom="0.8em",
            ),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("#", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="40px"),
                            rx.table.column_header_cell(rx.text("Question", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), min_width="200px"),
                            rx.table.column_header_cell(rx.text("CO", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="60px"),
                            rx.table.column_header_cell(rx.text("LO", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="60px"),
                            rx.table.column_header_cell(rx.text("Knowledge Type", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="110px"),
                            rx.table.column_header_cell(rx.text("Domain", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="130px"),
                            rx.table.column_header_cell(rx.text("RBT Level", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="90px"),
                            rx.table.column_header_cell(rx.text("Your Answer", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), min_width="160px"),
                            rx.table.column_header_cell(rx.text("Correct Answer", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), min_width="160px"),
                            rx.table.column_header_cell(rx.text("Marks", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="70px"),
                            rx.table.column_header_cell(rx.text("Status", font_family=FONT_BODY, size="1", weight="bold", color=COLORS["slate"]), width="90px"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            CandidateResultsState.question_items,
                            lambda q: rx.table.row(
                                rx.table.cell(rx.text(q["idx"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["question"], font_family=FONT_BODY, size="2", color=COLORS["ink"], weight="medium")),
                                rx.table.cell(rx.text(q["co"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["lo"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["knowledge_type"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["domain"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["rbt_level"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["candidate_answer"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["correct_answer"], font_family=FONT_BODY, size="2", color=COLORS["slate"])),
                                rx.table.cell(rx.text(q["marks"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"])),
                                rx.table.cell(
                                    rx.badge(
                                        q["status"],
                                        color_scheme=q["status_color"],
                                        variant="soft",
                                        size="1",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                overflow_x="auto",
                width="100%",
            ),
            spacing="0",
            width="100%",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.2em",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Tab Navigation Pill
# ─────────────────────────────────────────────────────────────────────────────

def _tab_pill(tab_key: str, label: str, icon_name: str) -> rx.Component:
    is_active = CandidateResultsState.active_tab == tab_key
    return rx.box(
        rx.hstack(
            rx.icon(icon_name, size=14, color=rx.cond(is_active, "white", "#64748B")),
            rx.text(
                label,
                font_family=FONT_BODY,
                size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, "white", "#475467"),
            ),
            spacing="2",
            align_items="center",
        ),
        background=rx.cond(is_active, "#6366F1", "#F1F5F9"),
        padding="0.5em 1.2em",
        border_radius="8px",
        cursor="pointer",
        on_click=CandidateResultsState.set_active_tab(tab_key),
        _hover={"background": rx.cond(is_active, "#4F46E5", "#E2E8F0")},
        transition="all 0.15s ease",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Result Not Available Empty State Card
# ─────────────────────────────────────────────────────────────────────────────

def _result_not_available_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon("file-clock", size=32, color="#6366F1"),
                background="#EEF2FF",
                padding="0.9em",
                border_radius="12px",
            ),
            rx.text(
                "Result Not Available Yet",
                font_family=FONT_DISPLAY,
                size="4",
                weight="bold",
                color=COLORS["ink"],
            ),
            rx.text(
                "The evaluation results for " + CandidateResultsState.selected_test_name + " have not been finalized yet. Once your facilitator completes and finalizes the evaluation, your score and detailed performance analytics will appear here.",
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
                text_align="center",
                max_width="480px",
            ),
            rx.button(
                rx.icon("arrow-left", size=14),
                "Back to Tests",
                size="2",
                variant="outline",
                color_scheme="gray",
                on_click=CandidateResultsState.clear_selected_test,
                cursor="pointer",
            ),
            spacing="3",
            align_items="center",
            justify="center",
            padding="3em 2em",
        ),
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Detailed Test Result Section
# ─────────────────────────────────────────────────────────────────────────────

def _test_result_detail_section() -> rx.Component:
    return rx.cond(
        CandidateResultsState.selected_test_name != "",
        rx.cond(
            CandidateResultsState.has_evaluated_selection,
            rx.vstack(
                # Header with back button, dates
                _test_detail_header(),

                # 4 Metrics cards
                _metric_cards_row(),

                # Performance tabs row
                rx.hstack(

                    _tab_pill("co", "CO", "activity"),
                    _tab_pill("lo", "LO", "target"),
                    _tab_pill("knowledge_type", "Knowledge Type", "box"),
                    _tab_pill("domain", "Domain", "star"),
                    _tab_pill("rbt_level", "RBT Level", "brain"),
                    _tab_pill("question_wise", "Question-wise", "file-text"),
                    spacing="2",
                    align_items="center",
                    wrap="wrap",
                    width="100%",
                    padding_y="0.5em",
                ),

                # Tab Content:
                rx.cond(
                    CandidateResultsState.active_tab == "co",
                    candidate_dimension_bar_chart(CandidateResultsState.chart_items_co, "Course Outcomes (CO) - Attainment"),
                    rx.cond(
                        CandidateResultsState.active_tab == "lo",
                        candidate_dimension_bar_chart(CandidateResultsState.chart_items_lo, "Learning Outcomes (LO) - Attainment"),
                        rx.cond(
                            CandidateResultsState.active_tab == "knowledge_type",
                            candidate_dimension_bar_chart(CandidateResultsState.chart_items_kt, "Knowledge Type Proficiency"),
                            rx.cond(
                                CandidateResultsState.active_tab == "domain",
                                candidate_dimension_bar_chart(CandidateResultsState.chart_items_domain, "Domain Competency"),
                                rx.cond(
                                    CandidateResultsState.active_tab == "rbt_level",
                                    candidate_dimension_bar_chart(CandidateResultsState.chart_items_rbt, "Revised Bloom's Taxonomy (RBT Level)"),
                                    # "question_wise" tab
                                    _question_wise_table(),
                                ),
                            ),
                        ),
                    ),
                ),

                spacing="4",
                width="100%",
                align_items="stretch",
            ),
            # Empty state if result data unavailable
            _result_not_available_card(),
        ),
        rx.fragment(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Main Candidate Results Page Component
# ─────────────────────────────────────────────────────────────────────────────

def candidate_results_page() -> rx.Component:
    """Master Candidate Results page displaying candidate's own finalized evaluations."""
    content = rx.vstack(
        _results_page_header(),
        _tests_in_assessment_card(),
        _test_result_detail_section(),
        spacing="4",
        width="100%",
        align_items="stretch",
        on_mount=CandidateResultsState.on_load,
    )
    return candidate_shell(
        active="results",
        title="My Results",
        subtitle="View your test results and performance analytics across completed assessments.",
        content=content,
    )
