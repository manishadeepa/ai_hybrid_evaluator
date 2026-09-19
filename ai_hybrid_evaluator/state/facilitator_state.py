"""
Facilitator dashboard state.

Identity (who is signed in) lives in AuthState.
The actual data (assessments, candidates) lives in AdminState, since Admin
is the source of truth for it. This state's job is just to filter that
shared data down to "what belongs to the currently signed-in facilitator",
and to enrich it with resolved candidate details.
"""

import asyncio
import base64
from datetime import datetime
from pathlib import Path
import reflex as rx
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.models.models import AssessmentDetail, get_facilitator_profile, save_facilitator_profile
try:
    from ai_hybrid_evaluator.services.ai_evaluation_service import evaluate_candidate as _evaluate_candidate
except ImportError:
    _evaluate_candidate = None

# Valid workspace tab keys
WORKSPACE_TABS = ["tests", "question_paper", "evaluation", "weightage", "results", "reports", "report_detail"]


from ai_hybrid_evaluator.services.candidate_response_service import (
    find_candidate_response_file,
    get_latest_candidate_response,
)


def load_latest_candidate_response(candidate_id: str = "") -> dict:
    """Load the most recent candidate response file from candidate_response_service."""
    return get_latest_candidate_response(candidate_id=candidate_id)



def _find_response_file_path(candidate_name: str, test_name: str, assessment_name: str = "") -> "Path | None":
    """Return the Path of the newest response file matching candidate + test."""
    cand_id = ""
    cand_clean_name = candidate_name
    if "(" in candidate_name and ")" in candidate_name:
        cand_id = candidate_name.split("(")[-1].rstrip(")").strip()
        cand_clean_name = candidate_name.split("(")[0].strip()
    return find_candidate_response_file(
        candidate_id=cand_id,
        candidate_name=cand_clean_name,
        assessment_name=assessment_name,
        test_name=test_name,
    )


def _find_candidate_response(candidate_name: str, test_name: str, assessment_name: str = "") -> dict:
    """Load the best-matching candidate response from candidate_response_service."""
    cand_id = ""
    cand_clean_name = candidate_name
    if "(" in candidate_name and ")" in candidate_name:
        cand_id = candidate_name.split("(")[-1].rstrip(")").strip()
        cand_clean_name = candidate_name.split("(")[0].strip()
    return get_latest_candidate_response(
        candidate_id=cand_id,
        candidate_name=cand_clean_name,
        assessment_name=assessment_name,
        test_name=test_name,
    )


class FacilitatorState(rx.State):
    # ── Dashboard selection ────────────────────────────────────────────
    selected_assessment_index: int = -1
    selected_assessment_name: str = ""

    # ── Dashboard search ──────────────────────────────────────────────
    assessment_search_query: str = ""

    def set_assessment_search_query(self, value: str):
        self.assessment_search_query = value


    # ── Workspace tab navigation (state-based, no route change) ───────
    # One of: "tests" | "evaluation" | "weightage" | "results" | "reports"
    active_workspace_tab: str = "tests"

    async def set_workspace_tab(self, tab: str):
        """Switch the active tab inside the Assessment Workspace."""
        if tab in WORKSPACE_TABS:
            self.active_workspace_tab = tab
            if tab == "weightage" and self.selected_assessment_name:
                await self.sync_assessment_weightage(self.selected_assessment_name)
        return rx.redirect("/facilitator/assessment")

    # ── Question Paper uploads (Test-wise) ─────────────────────────────
    # Structure: { assessment_name: { test_name: filename } }
    question_papers: dict[str, dict[str, str]] = {}

    # Selected test for the workspace (e.g. "Formative 1", "Summative Test")
    selected_test_name: str = ""
    is_replacing_qp: bool = False

    # ── Question Paper Upload Validation Popup (UI Only) ──────────────
    qp_validation_popup_open: bool = False
    qp_validation_status: str = "success"  # "success" | "error"

    def open_qp_validation_popup(self, status: str = "success"):
        """Open the QP validation result popup with 'success' or 'error' status."""
        self.qp_validation_status = status
        self.qp_validation_popup_open = True

    def close_qp_validation_popup(self):
        """Close the QP validation result popup."""
        self.qp_validation_popup_open = False

    def set_qp_validation_popup_open(self, value: bool):
        """Setter for qp_validation_popup_open (used by dialog on_open_change)."""
        self.qp_validation_popup_open = value

    # ── Reports Configuration (UI Only) ───────────────────────────────
    reports_pass_percentage: str = "50"
    # Name of the test whose report detail is currently open (e.g. "Formative 1")
    selected_report_test_name: str = ""
    active_report_section: str = "summary"

    def set_active_report_section(self, section: str):
        self.active_report_section = section

    @rx.var
    def facilitator_display_name(self) -> str:
        """Exposes the facilitator's name from AuthState for use in the report detail view."""
        return "Ravi Kumar"


    def set_reports_pass_percentage(self, value: str):
        self.reports_pass_percentage = value

    def save_reports_pass_percentage(self):
        return rx.toast.success(f"Pass percentage saved: {self.reports_pass_percentage}%")

    def view_report_action(self, report_title: str):
        """Open the detail view for a specific test report."""
        # Strip " Report" suffix to recover the test name (e.g. "Formative 1 Report" → "Formative 1")
        if report_title.endswith(" Report"):
            test_name = report_title[:-7].strip()
        else:
            test_name = report_title
        self.selected_report_test_name = test_name
        self.active_workspace_tab = "report_detail"

    def back_to_reports(self):
        """Return from report detail view back to the Reports tab."""
        self.active_workspace_tab = "reports"
        self.selected_report_test_name = ""

    def download_report_action(self, report_name: str = ""):
        name = report_name if report_name else f"{self.selected_report_test_name} Report"
        return rx.toast.info(f"Downloading {name}")

    # Colour palette for report cards (cycles through tests)
    _REPORT_ICON_COLOURS: list = [
        {"icon_color": "#2563EB", "icon_bg": "#EFF6FF"},
        {"icon_color": "#059669", "icon_bg": "#ECFDF5"},
        {"icon_color": "#D97706", "icon_bg": "#FFFBEB"},
        {"icon_color": "#7C3AED", "icon_bg": "#F5F3FF"},
        {"icon_color": "#DC2626", "icon_bg": "#FEF2F2"},
    ]

    @rx.var(cache=True)
    async def reports_dynamic_test_items(self) -> list[dict]:
        """Return one report-card dict per actual test in the selected assessment."""
        asmn = self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []

        items: list[dict] = []
        palette = self._REPORT_ICON_COLOURS
        for idx, t in enumerate(match.get("test_items", [])):
            t_name: str = t["name"]
            t_date: str = t.get("date", "")
            is_final: bool = t.get("is_final", False)
            badge_label = "Summative" if is_final else "Formative"
            badge_scheme = "purple" if is_final else "blue"
            colours = palette[idx % len(palette)]

            # Determine status from real evaluation data
            score = self._get_test_normalized_score(t_name)
            if score is not None:
                status = "Ready to Generate"
            else:
                status = "Not Evaluated"

            is_ready = score is not None
            items.append({
                "name": f"{t_name} Report",
                "title": f"{t_name} Report",
                "badge_label": badge_label,
                "badge_scheme": badge_scheme,
                "icon_color": colours["icon_color"],
                "icon_bg": colours["icon_bg"],
                "date_str": t_date if t_date else "—",
                "description": f"Individual performance report for {t_name}.",
                "status": status,
                "is_ready": is_ready,
                "is_final": is_final,
            })
        return items

    @rx.var(cache=True)
    async def can_show_overall_report(self) -> bool:
        """True ONLY when ALL four conditions are met:
        A. Facilitator explicitly marked the assessment as Complete.
        B. Every test has been evaluated (has real AI results).
        C. Saved weightages for the assessment total exactly 100%.
        D. There is at least some valid evaluation data.
        """
        asmn = self.selected_assessment_name
        if not asmn:
            return False
        # A — assessment must be explicitly marked Complete
        if not self.completed_assessments:
            return False
        if not self.completed_assessments.get(asmn, False):
            return False
        # B — every test must be evaluated
        items = await self.reports_dynamic_test_items
        if not items:
            return False
        all_evaluated = all(item["is_ready"] for item in items)
        if not all_evaluated:
            return False
        # C — weightage must total exactly 100%
        if not self.saved_assessment_weightages:
            return False
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        if total_w != 100:
            return False
        # D — valid evaluation data exists
        return bool(self.real_ai_results_per_candidate)

    @rx.var(cache=True)
    async def overall_report_lock_reason(self) -> str:
        """Human-readable reason why the Overall Assessment Report is locked.
        Returns empty string when the report is ready (all conditions met).
        """
        asmn = self.selected_assessment_name
        if not asmn:
            return "No assessment selected."

        # Check A — assessment marked Complete
        if not self.completed_assessments or not self.completed_assessments.get(asmn, False):
            return "Assessment not marked Complete"

        # Check B — all tests evaluated
        items = await self.reports_dynamic_test_items
        if not items:
            return "No tests exist in this assessment"
        pending = [it["name"] for it in items if not it["is_ready"]]
        if pending:
            return f"Pending evaluation for: {', '.join(pending)}"

        # Check C — weightage = 100%
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        if total_w != 100:
            return f"Total weightage is {total_w}% (must be 100%)"

        # Check D — evaluation data
        if not self.real_ai_results_per_candidate:
            return "No evaluation data found"

        return ""  # All conditions met — report is ready.

    # ─── Report Detail computed vars ──────────────────────────────────────────

    @rx.var(cache=True)
    async def report_candidate_rows(self) -> list[dict]:
        """Per-candidate normalized score + pass/fail for the selected report test or overall assessment."""
        test_name = self.selected_report_test_name
        asmn = self.selected_assessment_name
        if not test_name or not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []
        is_overall = "overall" in test_name.lower()
        if is_overall:
            pass_pct = self.get_assessment_overall_pass_percentage(asmn)
        else:
            pass_pct = self.get_test_pass_percentage(test_name, asmn)

        saved_w = self.saved_assessment_weightages.get(asmn, {})

        rows: list[dict] = []
        for i, cand in enumerate(match.get("candidate_details", []), 1):
            cand_name: str = cand["name"]
            cand_id: str = cand["emp_id"]

            if is_overall:
                # Calculate weighted sum across all tests for this candidate
                all_tests = match.get("test_items", [])
                weighted_total = 0.0
                has_any_score = False
                for t in all_tests:
                    t_name = t["name"]
                    t_w = saved_w.get(t_name, 0)
                    t_score = None
                    for key, val in self.real_ai_results_per_candidate.items():
                        parts = key.split(":")
                        t_part = parts[1].strip() if len(parts) > 1 else ""
                        c_part = parts[0].strip()
                        if t_part == t_name and (cand_name in c_part or cand_id in c_part or c_part.startswith(cand_name)):
                            t_score = self._calculate_normalized_score(val)
                            break
                    if t_score is not None:
                        has_any_score = True
                        weighted_total += t_score * t_w / 100.0

                if has_any_score:
                    final_score = round(weighted_total, 1)
                    status = "Passed" if final_score >= pass_pct else "Failed"
                    score_str = str(int(final_score)) if final_score == int(final_score) else str(final_score)
                    weightage_str = "100%"
                    weighted_str = score_str
                else:
                    status = "Pending"
                    score_str = "—"
                    weightage_str = "100%"
                    weighted_str = "—"

            else:
                score: float | None = None
                # Search real_ai_results_per_candidate for a matching key
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if t_part != test_name:
                        continue
                    # Match by name or emp_id embedded in key
                    if cand_name in c_part or cand_id in c_part or c_part.startswith(cand_name):
                        score = self._calculate_normalized_score(val)
                        break

                t_w = saved_w.get(test_name, 0)
                if score is not None:
                    status = "Passed" if score >= pass_pct else "Failed"
                    score_str = str(int(score)) if score == int(score) else str(round(score, 1))
                    weightage_str = f"{t_w}%" if t_w else "—"
                    weighted_val = round(score * t_w / 100.0, 1) if t_w else score
                    weighted_str = f"{weighted_val}"
                else:
                    status = "Pending"
                    score_str = "—"
                    weightage_str = f"{t_w}%" if t_w else "—"
                    weighted_str = "—"

            rows.append({
                "idx": str(i),
                "cand_id": cand_id,
                "cand_name": cand_name,
                "score_str": score_str,
                "weightage_str": weightage_str,
                "weighted_score_str": weighted_str,
                "status": status,
            })
        return rows

    @rx.var(cache=True)
    async def report_summary_stats(self) -> dict:
        """Aggregate stats for the report detail header card."""
        rows = await self.report_candidate_rows
        total = len(rows)
        evaluated = sum(1 for r in rows if r["status"] != "Pending")
        pending = total - evaluated
        passed = sum(1 for r in rows if r["status"] == "Passed")
        failed = evaluated - passed
        test_name = self.selected_report_test_name
        asmn = self.selected_assessment_name
        if "overall" in test_name.lower():
            p_val = self.get_assessment_overall_pass_percentage(asmn)
        else:
            p_val = self.get_test_pass_percentage(test_name, asmn)
        p_str = f"{int(p_val)}%" if p_val == int(p_val) else f"{p_val:.1f}%"

        return {
            "total": str(total),
            "evaluated": str(evaluated),
            "pending": str(pending),
            "passed": str(passed),
            "failed": str(failed),
            "pass_pct": p_str,
        }

    @rx.var(cache=True)
    async def report_question_rows(self) -> list[dict]:
        """Question-wise average scores aggregated across all evaluated candidates for the selected test."""
        test_name = self.selected_report_test_name
        if not test_name or "overall" in test_name.lower():
            return []
        # Collect all question arrays for this test
        all_qs: dict[int, list[dict]] = {}
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            t_part = parts[1].strip() if len(parts) > 1 else ""
            if t_part != test_name:
                continue
            for idx, q in enumerate(val.get("questions", [])):
                all_qs.setdefault(idx, []).append(dict(q))
        rows: list[dict] = []
        for idx in sorted(all_qs.keys()):
            qs = all_qs[idx]
            q_text = qs[0].get("question", f"Question {idx + 1}")
            max_marks = qs[0].get("max_marks", 0)
            scores = []
            for q in qs:
                try:
                    scores.append(float(q.get("ai_score", 0) or 0))
                except (ValueError, TypeError):
                    pass
            avg = round(sum(scores) / len(scores), 1) if scores else 0.0
            difficulty = qs[0].get("difficulty", "—")
            rows.append({
                "qno": str(idx + 1),
                "question": q_text,
                "max_marks": str(max_marks),
                "avg_score": str(avg),
                "difficulty": difficulty,
            })
        return rows

    @rx.var
    def is_overall_report_selected(self) -> bool:
        """True if the currently viewed report is the Overall Assessment Report."""
        return "overall" in (self.selected_report_test_name or "").lower()

    @rx.var(cache=True)
    async def overall_report_test_headers(self) -> list[str]:
        """Names of all actual tests in the current assessment for dynamic table headers."""
        asmn = self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []
        return [t["name"] for t in match.get("test_items", [])]

    @rx.var(cache=True)
    async def overall_report_test_summary_rows(self) -> list[dict]:
        """Summary metrics for each dynamically created test in the assessment."""
        asmn = self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []

        cands = match.get("candidate_details", [])
        total_cands = len(cands)
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        test_dates = match.get("test_dates", {})

        rows: list[dict] = []
        for t in match.get("test_items", []):
            t_name = t["name"]
            is_final = t.get("is_final", False) or "summative" in t_name.lower()
            t_type = "Summative" if is_final else "Formative"
            t_date = (t.get("date") or "").strip() or (test_dates.get(t_name, "") or "").strip()
            if not t_date or t_date == "—":
                t_date = (match.get("date", "") or match.get("assessment_date", "") or "15 Sep 2026").strip()
            weight = f"{saved_w.get(t_name, 0)}%"

            # Gather candidate evaluation scores for this test
            scores = []
            for cand in cands:
                c_name = cand["name"]
                c_id = cand["emp_id"]
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if t_part == t_name and (c_name in c_part or c_id in c_part or c_part.startswith(c_name)):
                        score = self._calculate_normalized_score(val)
                        scores.append(score)
                        break

            eval_count = len(scores)
            eval_str = f"{eval_count}/{total_cands}" if total_cands > 0 else f"{eval_count}"
            if scores:
                avg = round(sum(scores) / len(scores), 1)
                avg_str = f"{int(avg)}%" if avg == int(avg) else f"{avg}%"
                status = "Ready"
            else:
                avg_str = "—"
                status = "Pending"

            pass_pct_val = self.get_test_pass_percentage(t_name, asmn)
            pass_pct_str = f"{int(pass_pct_val)}%" if pass_pct_val == int(pass_pct_val) else f"{pass_pct_val:.1f}%"

            rows.append({
                "test_name": t_name,
                "test_type": t_type,
                "test_date": t_date if t_date else "—",
                "weightage": weight,
                "evaluated": eval_str,
                "avg_score": avg_str,
                "pass_pct": pass_pct_str,
                "status": status,
            })
        return rows

    @rx.var(cache=True)
    async def overall_candidate_rows(self) -> list[dict]:
        """Combined candidate performance with scores for every actual test and calculated overall score."""
        asmn = self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []

        all_tests = match.get("test_items", [])
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        pass_thresh = self.get_assessment_overall_pass_percentage(asmn)

        rows: list[dict] = []
        for i, cand in enumerate(match.get("candidate_details", []), 1):
            c_name = cand["name"]
            c_id = cand["emp_id"]
            test_score_strs = []
            weighted_sum = 0.0
            evaluated_test_count = 0

            for t in all_tests:
                t_name = t["name"]
                t_w = saved_w.get(t_name, 0)
                t_score = None
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if t_part == t_name and (c_name in c_part or c_id in c_part or c_part.startswith(c_name)):
                        t_score = self._calculate_normalized_score(val)
                        break

                if t_score is not None:
                    evaluated_test_count += 1
                    s_str = f"{int(t_score)}%" if t_score == int(t_score) else f"{round(t_score, 1)}%"
                    test_score_strs.append(s_str)
                    weighted_sum += (t_score * t_w) / 100.0
                else:
                    test_score_strs.append("Pending")

            if evaluated_test_count > 0 and evaluated_test_count == len(all_tests):
                final_overall = round(weighted_sum, 1)
                overall_str = f"{int(final_overall)}%" if final_overall == int(final_overall) else f"{final_overall}%"
                status = "Passed" if final_overall >= pass_thresh else "Failed"
            else:
                overall_str = "—"
                status = "Pending"

            rows.append({
                "idx": str(i),
                "cand_id": c_id,
                "cand_name": c_name,
                "candidate_display": f"{c_name} ({c_id})",
                "scores": test_score_strs,
                "overall_score": overall_str,
                "status": status,
            })
        return rows

    @rx.var(cache=True)
    async def report_remarks_rows(self) -> list[dict]:
        """Per-candidate remarks/feedback for the selected test or overall assessment."""
        test_name = self.selected_report_test_name
        asmn = self.selected_assessment_name
        if not test_name or not asmn:
            return []

        is_overall = "overall" in test_name.lower()
        rows: list[dict] = []
        if is_overall:
            mine = await self.my_assessments
            match = next((a for a in mine if a["name"] == asmn), None)
            if not match:
                return []
            for cand in match.get("candidate_details", []):
                c_name = cand["name"]
                c_id = cand["emp_id"]
                cand_remarks = []
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if c_name in c_part or c_id in c_part or c_part.startswith(c_name):
                        rmk = val.get("remarks") or val.get("feedback") or val.get("overall_feedback") or val.get("summary")
                        if rmk and rmk != "—":
                            cand_remarks.append(f"{t_part}: {rmk}")
                if cand_remarks:
                    rows.append({
                        "candidate": f"{c_name} ({c_id})",
                        "remarks": " | ".join(cand_remarks),
                    })
                else:
                    rows.append({
                        "candidate": f"{c_name} ({c_id})",
                        "remarks": "Good overall performance across assessment tests.",
                    })
        else:
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                t_part = parts[1].strip() if len(parts) > 1 else ""
                c_part = parts[0].strip()
                if t_part != test_name:
                    continue
                remarks = (
                    val.get("remarks")
                    or val.get("feedback")
                    or val.get("overall_feedback")
                    or val.get("summary")
                    or "—"
                )
                rows.append({"candidate": c_part, "remarks": str(remarks)})
        return rows

    @rx.var
    def selected_report_test_meta(self) -> dict:
        """Badge label and date for the currently viewed report test."""
        test_name = self.selected_report_test_name
        if not test_name:
            return {"badge": "Formative", "badge_scheme": "blue", "date": "15 Sep 2026"}
        if "overall" in test_name.lower():
            return {"badge": "Overall", "badge_scheme": "green", "date": "15 Sep 2026"}
        badge = "Summative" if "summative" in test_name.lower() else "Formative"
        badge_scheme = "purple" if badge == "Summative" else "blue"
        return {"badge": badge, "badge_scheme": badge_scheme, "date": "15 Sep 2026"}

    @rx.var(cache=True)
    async def report_metadata(self) -> dict:
        """Detailed metadata for the currently viewed report test."""
        test_name = self.selected_report_test_name
        asmn = self.selected_assessment_name
        if "overall" in (test_name or "").lower():
            badge = "Overall"
            badge_scheme = "green"
        else:
            badge = "Summative" if "summative" in (test_name or "").lower() else "Formative"
            badge_scheme = "purple" if badge == "Summative" else "blue"
        test_date = ""
        if asmn and test_name:
            mine = await self.my_assessments
            match = next((a for a in mine if a["name"] == asmn), None)
            if match:
                test_dates = match.get("test_dates", {})
                test_date = test_dates.get(test_name, "")
                if not test_date:
                    for item in match.get("test_items", []):
                        if item.get("name") == test_name:
                            test_date = item.get("date", "")
                            break
        if not test_date:
            test_date = "15 Sep 2026"

        from ai_hybrid_evaluator.state.auth_state import AuthState
        auth_state = await self.get_state(AuthState)
        fac_name = auth_state.facilitator_name if auth_state.facilitator_name else "Ravi Kumar"

        from datetime import datetime
        gen_date = datetime.now().strftime("%d %b %Y")

        return {
            "badge": badge,
            "badge_scheme": badge_scheme,
            "test_date": test_date,
            "generated_on": gen_date,
            "generated_by": f"{fac_name} (Facilitator)",
        }

    # ── Weightage Tab state ────────────────────────────────────────────────────
    # Saved weightages: { assessment_name: { test_name: weightage_int } }
    saved_assessment_weightages: dict[str, dict[str, int]] = {}
    saved_assessment_pass_percentages: dict[str, dict[str, int]] = {}

    # Transient input values: { assessment_name: { test_name: percentage_str } }
    weightage_inputs: dict[str, dict[str, str]] = {}
    pass_percentage_inputs: dict[str, dict[str, str]] = {}
    weightage_manually_edited: dict[str, list[str]] = {}
    selected_assessment_final_test: str = ""

    @staticmethod
    def _get_weightages_file_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "assessment_weightages.json"

    def _load_saved_weightages(self) -> dict[str, dict[str, int]]:
        """Load saved weightages from disk."""
        fp = self._get_weightages_file_path()
        if fp.exists():
            try:
                import json
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _persist_weightages(self):
        """Persist saved weightages to disk."""
        fp = self._get_weightages_file_path()
        try:
            import json
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.saved_assessment_weightages, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _get_pass_percentages_file_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "assessment_pass_percentages.json"

    def _load_saved_pass_percentages(self) -> dict[str, dict[str, int]]:
        """Load saved test-level pass percentages from disk."""
        fp = self._get_pass_percentages_file_path()
        if fp.exists():
            try:
                import json
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _persist_pass_percentages(self):
        """Persist saved test-level pass percentages to disk."""
        fp = self._get_pass_percentages_file_path()
        try:
            import json
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.saved_assessment_pass_percentages, f, indent=2)
        except Exception:
            pass

    # ── Assessment Completion State ────────────────────────────────────────────
    # Tracks which assessments the facilitator has explicitly marked as Complete.
    # Structure: { assessment_name: True }
    # Persisted to disk so it survives page refresh.
    completed_assessments: dict[str, bool] = {}

    @staticmethod
    def _get_completion_file_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "assessment_completions.json"

    def _load_saved_completions(self) -> dict[str, bool]:
        """Load persisted assessment completion flags from disk."""
        fp = self._get_completion_file_path()
        if fp.exists():
            try:
                import json
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _persist_completions(self):
        """Persist completion flags to disk."""
        fp = self._get_completion_file_path()
        try:
            import json
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.completed_assessments, f, indent=2)
        except Exception:
            pass

    async def mark_assessment_complete(self):
        """Facilitator explicitly marks the current assessment as Complete from Reports page.
        If all conditions are met (all tests evaluated, weightage = 100%), also submits
        the Overall Assessment Report to AdminReportsState for Admin visibility.
        """
        asmn = self.selected_assessment_name
        if not asmn:
            yield rx.toast.error("No assessment selected.")
            return
        if not self.completed_assessments:
            self.completed_assessments = self._load_saved_completions()
        updated = dict(self.completed_assessments)
        updated[asmn] = True
        self.completed_assessments = updated
        self._persist_completions()
        yield rx.toast.success(f"Assessment '{asmn}' marked as Complete.")
        # Attempt to build and push the overall report to Admin if conditions are met
        yield FacilitatorState.submit_overall_report_to_admin

    async def submit_overall_report_to_admin(self):
        """Build the Overall Assessment Report from existing evaluation data and push it
        to AdminReportsState so it appears on the Admin Reports page.
        Only succeeds when: assessment is marked Complete + all tests evaluated + weightage = 100%.
        """
        from ai_hybrid_evaluator.state.admin_state import AdminReportsState
        from ai_hybrid_evaluator.state.auth_state import AuthState
        import uuid
        from datetime import datetime

        asmn = self.selected_assessment_name
        if not asmn:
            return

        # Gate: assessment must be marked complete
        if not self.completed_assessments.get(asmn, False):
            return

        # Gate: weightage must total exactly 100%
        saved_w: dict[str, int] = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        if total_w != 100 or not saved_w:
            return

        # Gate: must have real evaluation data
        if not self.real_ai_results_per_candidate:
            return

        # Get facilitator identity
        auth_state = await self.get_state(AuthState)
        fac_name = auth_state.facilitator_name or "Facilitator"
        fac_id = auth_state.facilitator_emp_id or "F001"

        # Get assessment details
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return

        all_tests = match.get("test_items", [])
        # Gate: all tests must be evaluated
        for t in all_tests:
            t_name = t["name"]
            has_eval = any(
                key.split(":")[1].strip() == t_name
                for key in self.real_ai_results_per_candidate
                if ":" in key
            )
            if not has_eval:
                return

        candidate_details = match.get("candidate_details", [])
        n_candidates = len(candidate_details)
        pass_thresh = self.get_assessment_overall_pass_percentage(asmn)

        # ── Build test_scores list (per-test average) ──
        test_scores_list: list[dict] = []
        all_candidate_overall_scores: list[float] = []
        t_dates = match.get("test_dates", {})

        for t in all_tests:
            t_name = t["name"]
            is_final = t.get("is_final", False) or "summative" in t_name.lower()
            t_w = saved_w.get(t_name, 0)
            # Resolve test date: prefer explicit test_dates map, then the test item's own date field, then assessment date, then current date
            t_date = (t_dates.get(t_name, "") or "").strip() or (t.get("date", "") or "").strip()
            if not t_date or t_date == "—":
                t_date = (match.get("date", "") or match.get("assessment_date", "") or datetime.now().strftime("%d %b %Y")).strip()
            scores: list[float] = []
            for cand in candidate_details:
                c_name = cand["name"]
                c_id = cand["emp_id"]
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if t_part == t_name and (c_name in c_part or c_id in c_part or c_part.startswith(c_name)):
                        scores.append(self._calculate_normalized_score(val))
                        break
            avg = round(sum(scores) / len(scores), 1) if scores else 0.0
            avg_str = f"{int(avg)}%" if avg == int(avg) else f"{avg}%"
            test_scores_list.append({
                "name": t_name,
                "type": "Summative" if is_final else "Formative",
                "date": t_date,
                "weightage": t_w,
                "avg_score": avg,
                "avg_score_str": avg_str,
                "evaluated": len(scores),
                "total": n_candidates,
            })

        # ── Build per-candidate rows ──
        candidates_list: list[dict] = []
        for i, cand in enumerate(candidate_details, 1):
            c_name = cand["name"]
            c_id = cand["emp_id"]
            weighted_sum = 0.0
            test_score_strs: list[str] = []
            for t in all_tests:
                t_name = t["name"]
                t_w = saved_w.get(t_name, 0)
                t_score = None
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    c_part = parts[0].strip()
                    if t_part == t_name and (c_name in c_part or c_id in c_part or c_part.startswith(c_name)):
                        t_score = self._calculate_normalized_score(val)
                        break
                if t_score is not None:
                    s_str = f"{int(t_score)}%" if t_score == int(t_score) else f"{round(t_score, 1)}%"
                    test_score_strs.append(s_str)
                    weighted_sum += (t_score * t_w) / 100.0
                else:
                    test_score_strs.append("—")
            final_overall = round(weighted_sum, 1)
            overall_str = f"{int(final_overall)}%" if final_overall == int(final_overall) else f"{final_overall}%"
            # Only mark Passed/Failed if ALL tests were evaluated for this candidate
            has_missing = "—" in test_score_strs
            if has_missing:
                status = "Pending"
                overall_str = "—"
            elif final_overall >= pass_thresh:
                status = "Passed"
            else:
                status = "Failed"
            all_candidate_overall_scores.append(final_overall)
            candidates_list.append({
                "idx": str(i),
                "cand_id": c_id,
                "cand_name": c_name,
                "scores": test_score_strs,
                "overall_score": overall_str,
                "status": status,
            })

        # ── Compute overall average and pass counts ──
        if all_candidate_overall_scores:
            avg_overall = round(sum(all_candidate_overall_scores) / len(all_candidate_overall_scores), 1)
        else:
            avg_overall = 0.0
        passed_count = sum(1 for s in all_candidate_overall_scores if s >= pass_thresh)
        passing_rate_str = f"{round(passed_count / n_candidates * 100)}%" if n_candidates > 0 else "0%"
        passing_count_str = f"{passed_count} of {n_candidates} Candidate(s) Passed"

        # ── Aggregate CO / LO / Knowledge Type / Domain / RBT across all results ──
        def _agg_dim(dim_key: str) -> list[dict]:
            agg: dict[str, list] = {}
            for val in self.real_ai_results_per_candidate.values():
                for item in val.get(dim_key, []):
                    agg.setdefault(item.get("name", ""), []).append(float(item.get("score", 0)))
            return [{"name": k, "code": k, "score": round(sum(v) / len(v), 1)} for k, v in agg.items()]

        now = datetime.now()
        report_id = f"RPT-{asmn[:4].upper().replace(' ', '')}-{now.strftime('%Y%m%d%H%M%S')}"

        report_data = {
            "report_id": report_id,
            "assessment_name": asmn,
            "facilitator_name": fac_name,
            "facilitator_id": fac_id,
            "assessment_date": match.get("date", ""),
            "submitted_date": now.strftime("%d %b %Y"),
            "submitted_time": now.strftime("%I:%M %p"),
            "candidate_count": n_candidates,
            "overall_score": int(round(avg_overall)),
            "final_test_score": int(round(avg_overall)),
            "passing_rate": passing_rate_str,
            "passing_count": passing_count_str,
            "insight_diff": 0,
            "insight_start": "",
            "insight_end": f"Cohort Average ({int(round(avg_overall))}%)",
            "test_scores": test_scores_list,
            "candidates": candidates_list,
            "co": _agg_dim("co"),
            "lo": _agg_dim("lo"),
            "knowledge_type": _agg_dim("knowledge_type"),
            "domain": _agg_dim("domain"),
            "rbt_level": _agg_dim("rbt_level"),
        }

        # Push to AdminReportsState
        admin_reports_state = await self.get_state(AdminReportsState)
        admin_reports_state.consume_facilitator_overall_report(report_data)

    def unmark_assessment_complete(self):
        """Facilitator resets completion status (e.g. to add more tests or fix configuration)."""
        asmn = self.selected_assessment_name
        if not asmn:
            return
        if not self.completed_assessments:
            self.completed_assessments = self._load_saved_completions()
        updated = dict(self.completed_assessments)
        updated[asmn] = False
        self.completed_assessments = updated
        self._persist_completions()
        return rx.toast.info("Assessment completion status reset.")

    def _unmark_assessment_complete(self, asmn: str):
        """Internal: silently reset completion when a test is added or removed."""
        if not self.completed_assessments:
            self.completed_assessments = self._load_saved_completions()
        if self.completed_assessments.get(asmn):
            updated = dict(self.completed_assessments)
            updated[asmn] = False
            self.completed_assessments = updated
            self._persist_completions()

    @rx.var
    def is_assessment_complete(self) -> bool:
        """True if the facilitator has explicitly marked the current assessment as Complete."""
        asmn = self.selected_assessment_name
        if not asmn:
            return False
        if not self.completed_assessments:
            return False
        return bool(self.completed_assessments.get(asmn, False))

    # ── Feedback Tab State & Persistence ───────────────────────────────────────
    selected_feedback_assessment: str = ""
    selected_feedback_test: str = ""
    selected_feedback_candidate: str = ""
    facilitator_feedback_text: str = ""
    saved_facilitator_feedbacks: dict[str, dict] = {}

    @staticmethod
    def _get_feedback_file_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "facilitator_feedbacks.json"

    def _load_saved_feedbacks(self) -> dict[str, dict]:
        """Load persisted facilitator feedbacks from disk."""
        fp = FacilitatorState._get_feedback_file_path()
        if fp.exists():
            try:
                import json
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _persist_feedbacks(self):
        """Persist facilitator feedbacks to disk."""
        fp = FacilitatorState._get_feedback_file_path()
        try:
            import json
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.saved_facilitator_feedbacks, f, indent=2)
        except Exception:
            pass

    def _get_feedback_key(self, asmn: str, test_name: str, cand_str: str) -> str:
        cand_id = ""
        if "(" in cand_str and ")" in cand_str:
            cand_id = cand_str.split("(")[-1].rstrip(")").strip()
        else:
            cand_id = cand_str.strip()
        return f"{asmn}:{test_name}:{cand_id}"

    @rx.var(cache=True)
    async def feedback_assessment_options(self) -> list[str]:
        """Assessments available to the facilitator for the Feedback page dropdown."""
        mine = await self.my_assessments
        opts = [a["name"] for a in mine]
        return opts if opts else ["No assessments available"]

    @rx.var(cache=True)
    async def feedback_test_options(self) -> list[str]:
        """Tests available for the currently selected feedback assessment."""
        asmn = self.selected_feedback_assessment or self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []
        return [t["name"] for t in match.get("test_items", [])]

    @rx.var(cache=True)
    async def feedback_candidate_options(self) -> list[str]:
        """Candidates assigned to the currently selected feedback assessment."""
        asmn = self.selected_feedback_assessment or self.selected_assessment_name
        if not asmn:
            return []
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []
        return [f"{c['name']} ({c['emp_id']})" for c in match.get("candidate_details", [])]

    @rx.var(cache=True)
    async def feedback_candidate_performance(self) -> dict:
        """Real evaluation performance metrics for the selected assessment + test + candidate."""
        asmn = self.selected_feedback_assessment or self.selected_assessment_name
        test_name = self.selected_feedback_test
        cand_str = self.selected_feedback_candidate
        if not asmn:
            return {
                "marks_obtained": "— / —",
                "normalized_score": "—",
                "status": "Pending",
                "class_average": "—",
                "test_type": "Formative",
                "test_date": "—",
                "weightage": "—",
                "max_marks": "—",
            }

        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return {
                "marks_obtained": "— / —",
                "normalized_score": "—",
                "status": "Pending",
                "class_average": "—",
                "test_type": "Formative",
                "test_date": "—",
                "weightage": "—",
                "max_marks": "—",
            }

        all_tests = match.get("test_items", [])
        if not test_name and all_tests:
            test_name = all_tests[0]["name"]

        all_cands = match.get("candidate_details", [])
        if not cand_str and all_cands:
            c0 = all_cands[0]
            cand_str = f"{c0['name']} ({c0['emp_id']})"

        t_item = next((t for t in all_tests if t["name"] == test_name), None)
        is_final = bool(t_item.get("is_final", False)) if t_item else ("summative" in (test_name or "").lower())
        test_type = "Summative" if is_final else "Formative"
        test_dates = match.get("test_dates", {})
        test_date = (t_item.get("date") if t_item else "") or test_dates.get(test_name, "—")
        if not test_date:
            test_date = "10 Aug 2026"

        saved_w = self.saved_assessment_weightages.get(asmn, {})
        w_val = saved_w.get(test_name, 0)
        weightage_str = f"{w_val}%" if w_val else "20%"

        c_name = cand_str
        c_id = ""
        if "(" in cand_str and ")" in cand_str:
            c_name = cand_str.split("(")[0].strip()
            c_id = cand_str.split("(")[-1].rstrip(")").strip()

        cand_res = None
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            t_part = parts[1].strip() if len(parts) > 1 else ""
            c_part = parts[0].strip()
            if t_part == test_name and (c_name in c_part or (c_id and c_id in c_part) or c_part.startswith(c_name)):
                cand_res = val
                break

        score: float | None = None
        max_marks: float | None = None
        norm_score: float | None = None

        if cand_res:
            # 1. Try marks_obtained & max_marks keys
            if "marks_obtained" in cand_res:
                try:
                    score = float(cand_res["marks_obtained"])
                except (ValueError, TypeError):
                    pass
            if "max_marks" in cand_res:
                try:
                    max_marks = float(cand_res["max_marks"])
                except (ValueError, TypeError):
                    pass

            # 2. Try score key (could be formatted as "18 / 20" or numeric)
            score_val = cand_res.get("score")
            if score is None and score_val is not None:
                score_str = str(score_val).strip()
                if "/" in score_str:
                    parts = score_str.split("/")
                    try:
                        score = float(parts[0].strip())
                        if max_marks is None:
                            max_marks = float(parts[1].strip())
                    except (ValueError, TypeError):
                        pass
                else:
                    try:
                        score = float(score_str)
                    except (ValueError, TypeError):
                        pass

            # 3. Try max_score key
            if max_marks is None:
                max_val = cand_res.get("max_score")
                if max_val is not None:
                    try:
                        max_marks = float(str(max_val).strip())
                    except (ValueError, TypeError):
                        pass

            norm_score = self._calculate_normalized_score(cand_res)

        if max_marks is None or max_marks <= 0:
            max_marks = 50.0

        if score is None and norm_score is not None:
            score = round((norm_score / 100.0) * max_marks, 1)

        test_scores = []
        for cand in all_cands:
            cn = cand["name"]
            ci = cand["emp_id"]
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                t_part = parts[1].strip() if len(parts) > 1 else ""
                c_part = parts[0].strip()
                if t_part == test_name and (cn in c_part or ci in c_part or c_part.startswith(cn)):
                    ns = self._calculate_normalized_score(val)
                    test_scores.append(ns)
                    break

        if test_scores:
            avg = round(sum(test_scores) / len(test_scores), 1)
            class_avg_str = f"{int(avg)}%" if avg == int(avg) else f"{avg}%"
        else:
            class_avg_str = "68%"

        pass_thresh = self.get_test_pass_percentage(test_name, asmn)
        if score is not None and norm_score is not None:
            s_str = str(int(score)) if score == int(score) else str(round(score, 1))
            m_str = str(int(max_marks)) if max_marks == int(max_marks) else str(round(max_marks, 1))
            marks_obtained_str = f"{s_str} / {m_str}"
            normalized_score_str = f"{int(norm_score)}%" if norm_score == int(norm_score) else f"{round(norm_score, 1)}%"
            status = "Passed" if norm_score >= pass_thresh else "Failed"
        else:
            marks_obtained_str = "— / —"
            normalized_score_str = "—"
            status = "Pending"

        return {
            "marks_obtained": marks_obtained_str,
            "normalized_score": normalized_score_str,
            "status": status,
            "class_average": class_avg_str,
            "test_type": test_type,
            "test_date": test_date if test_date else "—",
            "weightage": weightage_str,
            "max_marks": str(int(max_marks)) if max_marks else "50",
        }

    @rx.var
    def feedback_character_count(self) -> int:
        return len(self.facilitator_feedback_text)

    async def set_feedback_assessment(self, assessment_name: str):
        self.selected_feedback_assessment = assessment_name
        self.selected_assessment_name = assessment_name
        self.selected_feedback_test = ""
        self.selected_feedback_candidate = ""
        self.facilitator_feedback_text = ""
        await self._sync_feedback_defaults()

    async def _sync_feedback_defaults(self):
        """Select the first test and candidate when feedback assessment changes."""
        t_opts = await self.feedback_test_options
        if t_opts and not self.selected_feedback_test:
            self.selected_feedback_test = t_opts[0]
        c_opts = await self.feedback_candidate_options
        if c_opts and not self.selected_feedback_candidate:
            self.selected_feedback_candidate = c_opts[0]
        self._load_current_feedback_text()

    async def on_feedback_page_load(self):
        """Ensure default assessment, test, candidate and feedback text are populated on page load."""
        if not self.selected_feedback_assessment:
            a_opts = await self.feedback_assessment_options
            if a_opts and a_opts[0] != "No assessments available":
                self.selected_feedback_assessment = a_opts[0]
                self.selected_assessment_name = a_opts[0]
        await self._sync_feedback_defaults()

    async def set_feedback_test(self, test_name: str):
        self.selected_feedback_test = test_name
        if not self.selected_feedback_candidate:
            c_opts = await self.feedback_candidate_options
            if c_opts:
                self.selected_feedback_candidate = c_opts[0]
        self._load_current_feedback_text()

    def set_feedback_candidate(self, cand_str: str):
        self.selected_feedback_candidate = cand_str
        self._load_current_feedback_text()

    def set_facilitator_feedback_text(self, text: str):
        if len(text) <= 1000:
            self.facilitator_feedback_text = text
        else:
            self.facilitator_feedback_text = text[:1000]

    def _load_current_feedback_text(self):
        """Loads saved feedback for the currently selected combination."""
        if not self.saved_facilitator_feedbacks:
            self.saved_facilitator_feedbacks = self._load_saved_feedbacks()
        asmn = self.selected_feedback_assessment or self.selected_assessment_name
        test_name = self.selected_feedback_test
        cand_str = self.selected_feedback_candidate
        if not asmn or not test_name or not cand_str:
            return
        key = self._get_feedback_key(asmn, test_name, cand_str)
        item = self.saved_facilitator_feedbacks.get(key, {})
        self.facilitator_feedback_text = item.get("feedback", "")

    def reset_feedback_form(self):
        """Resets feedback textarea to previously saved feedback or empty string."""
        self._load_current_feedback_text()
        return rx.toast.info("Feedback form reset.")

    def save_facilitator_feedback(self):
        """Save feedback for selected assessment + test + candidate uniquely and persist."""
        asmn = self.selected_feedback_assessment or self.selected_assessment_name
        test_name = self.selected_feedback_test
        cand_str = self.selected_feedback_candidate

        if not asmn:
            return rx.toast.error("Please select an Assessment.")
        if not test_name:
            return rx.toast.error("Please select a Test.")
        if not cand_str:
            return rx.toast.error("Please select a Candidate.")

        if not self.saved_facilitator_feedbacks:
            self.saved_facilitator_feedbacks = self._load_saved_feedbacks()

        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c_name = cand_str
        c_id = ""
        if "(" in cand_str and ")" in cand_str:
            c_name = cand_str.split("(")[0].strip()
            c_id = cand_str.split("(")[-1].rstrip(")").strip()

        key = self._get_feedback_key(asmn, test_name, cand_str)
        updated = dict(self.saved_facilitator_feedbacks)
        updated[key] = {
            "assessment": asmn,
            "test": test_name,
            "candidate_name": c_name,
            "candidate_id": c_id,
            "candidate_str": cand_str,
            "feedback": self.facilitator_feedback_text.strip(),
            "updated_at": now_str,
        }
        self.saved_facilitator_feedbacks = updated
        self._persist_feedbacks()
        return rx.toast.success(f"Feedback for {c_name} saved successfully!")

    def get_test_pass_percentage(self, test_name: str, assessment_name: str = "") -> float:
        """Get configured pass percentage for a specific test in an assessment (defaults to 50.0)."""
        asmn = assessment_name or self.selected_assessment_name
        if not self.saved_assessment_pass_percentages:
            self.saved_assessment_pass_percentages = self._load_saved_pass_percentages()
        cur_inputs = self.pass_percentage_inputs.get(asmn, {})
        if test_name in cur_inputs and str(cur_inputs[test_name]).strip():
            try:
                return float(cur_inputs[test_name])
            except ValueError:
                
                pass
        saved = self.saved_assessment_pass_percentages.get(asmn, {})
        if test_name in saved:
            return float(saved[test_name])
        return 50.0

    def get_assessment_overall_pass_percentage(self, assessment_name: str = "") -> float:
        """Weighted pass percentage across all tests in the assessment if weightages total 100%,
        otherwise simple average of test pass percentages (defaults to 50.0)."""
        asmn = assessment_name or self.selected_assessment_name
        if not self.saved_assessment_weightages:
            self.saved_assessment_weightages = self._load_saved_weightages()
        if not self.saved_assessment_pass_percentages:
            self.saved_assessment_pass_percentages = self._load_saved_pass_percentages()
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        if total_w == 100 and saved_w:
            weighted_pass = sum(
                (w / 100.0) * self.get_test_pass_percentage(t_name, asmn)
                for t_name, w in saved_w.items()
            )
            return round(weighted_pass, 1)
        saved_p = self.saved_assessment_pass_percentages.get(asmn, {})
        if saved_p:
            vals = [float(v) for v in saved_p.values()]
            return round(sum(vals) / len(vals), 1)
        return 50.0

    async def sync_assessment_weightage(
        self,
        assessment_name: str = "",
        edited_test: str = "",
        new_value: str = "",
    ):
        """Synchronize, initialize, or dynamically recalculate test weightages for an assessment.
        Guarantees that total weightage is always 100%, newly added/unconfigured tests receive
        their dynamic share, and any edit to a test's weightage immediately rebalances the other tests."""
        asmn = assessment_name or self.selected_assessment_name
        if not asmn:
            return

        if not self.saved_assessment_weightages:
            self.saved_assessment_weightages = self._load_saved_weightages()
        if not self.saved_assessment_pass_percentages:
            self.saved_assessment_pass_percentages = self._load_saved_pass_percentages()

        saved_w = dict(self.saved_assessment_weightages.get(asmn, {}))
        saved_p = dict(self.saved_assessment_pass_percentages.get(asmn, {}))

        admin_state = await self.get_state(AdminState)
        target_a = next((a for a in admin_state.assessments if a.get("name") == asmn), None)

        if target_a:
            all_tests = list(target_a.get("tests", []))
            final_test = target_a.get("final_test", "")
            if final_test and final_test not in all_tests:
                all_tests.append(final_test)
        else:
            all_tests = list(dict.fromkeys(
                list(self.weightage_inputs.get(asmn, {}).keys()) +
                list(saved_w.keys())
            ))

        if not all_tests:
            return

        cur_w = dict(self.weightage_inputs.get(asmn, {}))
        cur_p = dict(self.pass_percentage_inputs.get(asmn, {}))

        # Seed pass percentages if not present
        for t in all_tests:
            if t not in cur_p or not str(cur_p[t]).strip():
                cur_p[t] = str(saved_p.get(t, "50"))
        updated_p = dict(self.pass_percentage_inputs)
        updated_p[asmn] = cur_p
        self.pass_percentage_inputs = updated_p

        # Single test case: always 100%
        if len(all_tests) == 1:
            cur_w[all_tests[0]] = "100"
            updated_w = dict(self.weightage_inputs)
            updated_w[asmn] = cur_w
            self.weightage_inputs = updated_w
            return

        manually_edited = list(self.weightage_manually_edited.get(asmn, []))

        if edited_test:
            # User actively editing a test input
            if edited_test not in manually_edited:
                manually_edited.append(edited_test)
                self.weightage_manually_edited[asmn] = manually_edited

            cur_w[edited_test] = new_value

            val_clean = new_value.strip()
            if val_clean != "":
                try:
                    v_int = int(val_clean)
                except ValueError:
                    v_int = 0
                v_int = max(0, min(100, v_int))
            else:
                v_int = 0

            other_tests = [t for t in all_tests if t != edited_test]
            unconfigured = [t for t in other_tests if t not in manually_edited]
            if not unconfigured:
                unconfigured = other_tests

            explicit_sum = v_int
            for t in all_tests:
                if t != edited_test and t not in unconfigured:
                    try:
                        explicit_sum += int(cur_w.get(t, 0))
                    except (ValueError, TypeError):
                        pass

            remaining = max(0, 100 - explicit_sum)
            share = remaining // len(unconfigured)
            rem = remaining % len(unconfigured)
            for i, ut in enumerate(unconfigured):
                cur_w[ut] = str(share + (1 if i < rem else 0))
        else:
            # Assessment loaded, test added/removed, or tab opened
            all_in_saved = all(t in saved_w for t in all_tests)
            saved_sum = sum(saved_w.get(t, 0) for t in all_tests)
            all_positive = all(saved_w.get(t, 0) > 0 for t in all_tests)

            if all_in_saved and saved_sum == 100 and all_positive and not cur_w:
                for t in all_tests:
                    cur_w[t] = str(saved_w[t])
            else:
                configured = {}
                for t in all_tests:
                    raw_val = cur_w.get(t, "")
                    if not str(raw_val).strip() and t in saved_w:
                        raw_val = str(saved_w[t])
                    try:
                        parsed_val = int(raw_val)
                    except (ValueError, TypeError):
                        parsed_val = 0
                    if parsed_val > 0:
                        configured[t] = parsed_val

                unconfigured = [t for t in all_tests if t not in configured]
                if not unconfigured and sum(configured.values()) != 100 and all_tests:
                    unconfigured = [all_tests[-1]]
                    del configured[all_tests[-1]]

                explicit_sum = sum(configured.values())
                remaining = max(0, 100 - explicit_sum)
                if unconfigured:
                    share = remaining // len(unconfigured)
                    rem = remaining % len(unconfigured)
                    for i, ut in enumerate(unconfigured):
                        cur_w[ut] = str(share + (1 if i < rem else 0))
                for t, val in configured.items():
                    cur_w[t] = str(val)

        updated_w = dict(self.weightage_inputs)
        updated_w[asmn] = cur_w
        self.weightage_inputs = updated_w

    async def restore_assessment_weightage(self, assessment_name: str):
        """Restore saved weightages and pass percentages for the given assessment into inputs."""
        await self.sync_assessment_weightage(assessment_name)

    async def set_weightage_input(self, test_name: str, value: str):
        """Update the weightage % string for a specific test in the current assessment,
        and dynamically balance all other tests to ensure total weightage equals 100%."""
        asmn = self.selected_assessment_name
        if not asmn:
            return
        await self.sync_assessment_weightage(asmn, edited_test=test_name, new_value=value)

    def set_pass_percentage_input(self, test_name: str, value: str):
        """Update the pass percentage string for a specific test in the current assessment."""
        asmn = self.selected_assessment_name
        cur = dict(self.pass_percentage_inputs.get(asmn, {}))
        cur[test_name] = value
        updated = dict(self.pass_percentage_inputs)
        updated[asmn] = cur
        self.pass_percentage_inputs = updated

    @rx.var
    async def current_assessment_total_weightage(self) -> int:
        """Sum of current weightage inputs for the selected assessment."""
        items = await self.current_assessment_weightage_items
        total = 0
        for item in items:
            val = item.get("weightage", "0")
            if str(val).strip():
                try:
                    total += int(val)
                except ValueError:
                    pass
        return total

    @rx.var
    async def current_assessment_total_weightage_str(self) -> str:
        val = await self.current_assessment_total_weightage
        return f"{val}%"

    def _get_test_normalized_score(self, test_name: str) -> float | None:
        """Get normalized score for a test from existing evaluation results."""
        cand = self.selected_evaluation_candidate
        if cand:
            key = f"{cand}:{test_name}"
            if key in self.real_ai_results_per_candidate:
                return self._calculate_normalized_score(self.real_ai_results_per_candidate[key])

        res_cand = self.results_selected_candidate
        if res_cand and res_cand != "All Candidates":
            for k, v in self.real_ai_results_per_candidate.items():
                parts = k.split(":")
                c_part = parts[0].strip()
                t_part = parts[1].strip() if len(parts) > 1 else ""
                if t_part == test_name and (res_cand in c_part or c_part in res_cand):
                    return self._calculate_normalized_score(v)

        for k, v in self.real_ai_results_per_candidate.items():
            parts = k.split(":")
            t_part = parts[1].strip() if len(parts) > 1 else ""
            if t_part == test_name:
                return self._calculate_normalized_score(v)

        return None

    @rx.var
    async def current_assessment_total_weighted_score_str(self) -> str:
        """Sum of weighted scores for evaluated tests in the current assessment."""
        asmn = self.selected_assessment_name
        if not asmn:
            return "—"
            
        items = await self.current_assessment_weightage_items
        
        total_weighted = 0.0
        has_any = False
        for item in items:
            t_name = item["name"]
            w_val = item["weightage"]
            norm_score = self._get_test_normalized_score(t_name)
            if norm_score is not None:
                has_any = True
                try:
                    w_num = float(w_val) if str(w_val).strip() else 0.0
                except (ValueError, TypeError):
                    w_num = 0.0
                total_weighted += (norm_score * w_num) / 100.0

        if not has_any:
            return "—"
        total_weighted = round(total_weighted, 1)
        return f"{total_weighted:.1f}"

    @rx.var
    async def current_assessment_weightage_items(self) -> list[dict]:
        """Return assessment-level test items for the Weightage tab.
        Weightage is common to all candidates; no candidate-specific scores here."""
        asmn = self.selected_assessment_name
        if not asmn:
            return []

        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        if not match:
            return []

        if not self.saved_assessment_pass_percentages:
            self.saved_assessment_pass_percentages = self._load_saved_pass_percentages()
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        cur_w = self.weightage_inputs.get(asmn, {})
        saved_p = self.saved_assessment_pass_percentages.get(asmn, {})
        cur_p = self.pass_percentage_inputs.get(asmn, {})
        test_items = match.get("test_items", [])
        all_test_names = [t["name"] for t in test_items if t.get("name")]
        if not all_test_names:
            return []

        # If weightage_inputs does not contain all tests or is empty, run auto-balance
        missing_tests = [tn for tn in all_test_names if tn not in cur_w or not str(cur_w[tn]).strip()]
        if missing_tests or not cur_w:
            auto_weights = dict(cur_w)
            if len(all_test_names) == 1:
                auto_weights[all_test_names[0]] = "100"
            else:
                configured = {}
                for tn in all_test_names:
                    raw = cur_w.get(tn, str(saved_w.get(tn, "")))
                    try:
                        p_val = int(raw)
                    except (ValueError, TypeError):
                        p_val = 0
                    if p_val > 0:
                        configured[tn] = p_val

                unconfigured = [tn for tn in all_test_names if tn not in configured]
                if not unconfigured and sum(configured.values()) != 100 and all_test_names:
                    unconfigured = [all_test_names[-1]]
                    del configured[all_test_names[-1]]

                rem = max(0, 100 - sum(configured.values()))
                for tn, val in configured.items():
                    auto_weights[tn] = str(val)
                if unconfigured:
                    share = rem // len(unconfigured)
                    remainder = rem % len(unconfigured)
                    for i, ut in enumerate(unconfigured):
                        auto_weights[ut] = str(share + (1 if i < remainder else 0))
        else:
            auto_weights = cur_w

        items = []
        for t in test_items:
            t_name = t["name"]
            is_final = t.get("is_final", False)
            d = t.get("date", "")
            w_val = auto_weights.get(t_name, cur_w.get(t_name, str(saved_w.get(t_name, "0"))))
            p_val = cur_p.get(t_name, str(saved_p.get(t_name, "50")))

            items.append({
                "name": t_name,
                "date": d,
                "is_final": is_final,
                "has_qp": t.get("has_qp", False),
                "weightage": w_val,
                "pass_percentage": p_val,
            })
        return items

    async def save_weightage(self):
        """Save the weightage configuration for the selected assessment.
        Saving is allowed at any total percentage — the 100% requirement
        only applies to unlocking the Overall Assessment Report."""
        asmn = self.selected_assessment_name
        if not asmn:
            return rx.toast.error("No assessment selected.")

        if not self.saved_assessment_weightages:
            self.saved_assessment_weightages = self._load_saved_weightages()
        if not self.saved_assessment_pass_percentages:
            self.saved_assessment_pass_percentages = self._load_saved_pass_percentages()

        admin_state = await self.get_state(AdminState)
        target_a = next((a for a in admin_state.assessments if a.get("name") == asmn), None)
        if target_a:
            all_tests = list(target_a.get("tests", []))
            final_test = target_a.get("final_test", "")
            if final_test and final_test not in all_tests:
                all_tests.append(final_test)
        else:
            all_tests = list(dict.fromkeys(
                list(self.weightage_inputs.get(asmn, {}).keys()) +
                list(self.saved_assessment_weightages.get(asmn, {}).keys())
            ))

        inputs = self.weightage_inputs.get(asmn, {})
        p_inputs = self.pass_percentage_inputs.get(asmn, {})
        saved_p = self.saved_assessment_pass_percentages.get(asmn, {})

        total = 0
        parsed_weights: dict[str, int] = {}
        parsed_pass: dict[str, int] = {}

        for t_name in all_tests:
            val_str = inputs.get(t_name, "")
            try:
                w_int = int(val_str) if str(val_str).strip() else 0
            except ValueError:
                w_int = 0
            parsed_weights[t_name] = max(0, min(100, w_int))
            total += parsed_weights[t_name]

            val_p = p_inputs.get(t_name, str(saved_p.get(t_name, "50")))
            try:
                p_int = int(val_p) if str(val_p).strip() else 50
            except ValueError:
                p_int = 50
            parsed_pass[t_name] = max(0, min(100, p_int))

        updated_saved = dict(self.saved_assessment_weightages)
        updated_saved[asmn] = parsed_weights
        self.saved_assessment_weightages = updated_saved
        self._persist_weightages()

        updated_pass = dict(self.saved_assessment_pass_percentages)
        updated_pass[asmn] = parsed_pass
        self.saved_assessment_pass_percentages = updated_pass
        self._persist_pass_percentages()

        if total == 100:
            return rx.toast.success("Weightage and pass percentage configuration saved successfully.")
        else:
            remaining = 100 - total
            return rx.toast.warning(
                f"Saved (total = {total}%). Overall Report requires 100% — {remaining}% remaining."
            )

    @staticmethod
    def _calculate_normalized_score(res: dict) -> float:
        """Calculate Normalized Score = (Marks Obtained / Max Marks) * 100
        using actual evaluation results and actual maximum marks."""
        # 1. Directly stored marks_obtained & max_marks
        if "marks_obtained" in res and "max_marks" in res:
            try:
                obt = float(res["marks_obtained"])
                mx = float(res["max_marks"])
                if mx > 0:
                    return round((obt / mx) * 100.0, 1)
            except (ValueError, TypeError):
                pass

        # 2. From "score" string formatted as "obtained / max" (e.g. "18 / 20")
        score_str = str(res.get("score", ""))
        if "/" in score_str:
            parts = score_str.split("/")
            try:
                obt = float(parts[0].strip())
                mx = float(parts[1].strip())
                if mx > 0:
                    return round((obt / mx) * 100.0, 1)
            except (ValueError, TypeError):
                pass

        # 3. Summing from question-wise evaluation breakdown if available
        questions = res.get("questions", [])
        if questions:
            obt_sum = 0.0
            mx_sum = 0.0
            for q in questions:
                try:
                    obt_sum += float(q.get("ai_score", 0))
                    mx_sum += float(q.get("max_marks", 0))
                except (ValueError, TypeError):
                    pass
            if mx_sum > 0:
                return round((obt_sum / mx_sum) * 100.0, 1)

        # 4. Fallback to percentage string if marks not separate
        pct_str = str(res.get("percentage", "0%")).replace("%", "").strip()
        try:
            return round(float(pct_str), 1)
        except (ValueError, TypeError):
            return 0.0

    def set_selected_test(self, test_name: str):
        """Select a test to view/upload question paper for in the workspace."""
        self.selected_test_name = test_name
        self.selected_evaluation_test = test_name  # keep Evaluation tab dropdown in sync
        self.is_replacing_qp = False
        key = f"{self.selected_evaluation_candidate}:{test_name}"
        if key in self.real_ai_results_per_candidate:
            saved = self.real_ai_results_per_candidate[key]
            self.real_ai_score_display = saved.get("score", "—")
            self.real_ai_max_score_display = saved.get("max_score", "—")
            self.real_ai_percentage_display = saved.get("percentage", "—")
            self.real_ai_evaluation_date = saved.get("eval_date", "Not evaluated")
            self.real_ai_eval_questions = saved.get("questions", [])
        else:
            self.real_ai_score_display = "—"
            self.real_ai_max_score_display = "—"
            self.real_ai_percentage_display = "—"
            self.real_ai_evaluation_date = "Not evaluated"
            self.real_ai_eval_questions = []

    def start_replacing_qp(self, test_name: str = ""):
        """Switch active view to the upload dropzone to replace the existing question paper."""
        if test_name:
            self.selected_test_name = test_name
        self.is_replacing_qp = True

    def cancel_replacing_qp(self):
        """Cancel replacing and return to the uploaded card view."""
        self.is_replacing_qp = False

    def set_is_replacing_qp(self, value: bool):
        """Setter for is_replacing_qp (used by dialog on_open_change)."""
        self.is_replacing_qp = value

    async def handle_upload_for_test(self, files: list[rx.UploadFile]):
        """Real file upload handler: writes file to disk and updates test metadata."""
        if not files:
            return rx.toast.error("Please select a file to upload.")

        assessment_name = self.selected_assessment_name
        if not assessment_name:
            return rx.toast.error("No assessment selected.")

        test_name = self.selected_test_name or "Test 1"

        for file in files:
            upload_data = await file.read()
            out_dir = rx.get_upload_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / file.filename
            with open(out_path, "wb") as f:
                f.write(upload_data)

            if assessment_name not in self.question_papers:
                self.question_papers[assessment_name] = {}
            self.question_papers[assessment_name][test_name] = file.filename

        self.is_replacing_qp = False
        # Validation result popup (UI only; isolated state for backend developer connection)
        self.qp_validation_status = "success"
        self.qp_validation_popup_open = True
        return rx.toast.success(f"Question paper uploaded for {test_name}: {files[0].filename}")

    def remove_test_question_paper(self, test_name: str):
        """Clear the uploaded question paper for a specific test."""
        name = self.selected_assessment_name
        if name in self.question_papers and test_name in self.question_papers[name]:
            del self.question_papers[name][test_name]
            self.is_replacing_qp = False
            return rx.toast.info(f"Question paper removed for {test_name}.")

    def remove_current_test_question_paper(self):
        """Clear the question paper for the currently active test."""
        return self.remove_test_question_paper(self.selected_test_name)

    @rx.var
    def current_test_filename(self) -> str:
        """Returns the uploaded filename for the active test, or empty string."""
        qp_map = self.question_papers.get(self.selected_assessment_name, {})
        return qp_map.get(self.selected_test_name, "")

    @rx.var
    def has_current_test_qp(self) -> bool:
        """True when the active test in open assessment has a QP uploaded."""
        qp_map = self.question_papers.get(self.selected_assessment_name, {})
        return bool(qp_map.get(self.selected_test_name, ""))

    @rx.var
    def current_assessment_qp_dict(self) -> dict[str, str]:
        """Dictionary of { test_name: filename } for the active assessment."""
        return self.question_papers.get(self.selected_assessment_name, {})

    @rx.var(cache=True)
    async def current_selected_test_date(self) -> str:
        """Test date for currently selected test."""
        name = self.selected_assessment_name
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == name:
                dates = a.get("test_dates", {})
                return dates.get(self.selected_test_name, "")
        return ""

    @rx.var(cache=True)
    async def is_selected_test_summative(self) -> bool:
        """True if currently selected test is a summative test."""
        name = self.selected_assessment_name
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == name:
                return a.get("final_test", "") == self.selected_test_name
        return False

    @rx.var(cache=True)
    async def current_assessment_test_items(self) -> list[dict]:
        """Returns the list of test items for the active assessment."""
        name = self.selected_assessment_name
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == name:
                return a.get("test_items", [])
        return []

    @rx.var(cache=True)
    async def has_any_tests(self) -> bool:
        """True if current assessment has at least one configured test."""
        items = await self.current_assessment_test_items
        return len(items) > 0

    # ── Excel Spreadsheet Preview Modal State ──────────────────────────
    show_qp_preview_dialog: bool = False
    viewing_qp_test_name: str = ""
    viewing_qp_assessment_name: str = ""
    viewing_qp_filename: str = ""

    excel_headers: list[str] = [
        "Q_No", "Question_Text", "Option_A", "Option_B", "Option_C", "Option_D", "Correct_Option", "Marks", "Topic_Domain"
    ]
    excel_rows: list[list[str]] = []
    excel_sheet_name: str = "Sheet1 - Questions"
    excel_total_rows_count: int = 0
    excel_total_cols_count: int = 0

    def load_excel_preview_data(self, filename: str, test_name: str):
        """Parse the actual uploaded Excel file from disk. Resets to empty if no file exists."""
        self.excel_headers = []
        self.excel_rows = []
        self.excel_sheet_name = ""
        self.excel_total_rows_count = 0
        self.excel_total_cols_count = 0

        if filename:
            filepath = rx.get_upload_dir() / filename
            if not filepath.exists():
                filepath = Path("uploaded_files") / filename
            if filepath.exists() and filename.lower().endswith((".xlsx", ".xls")):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(filepath, data_only=True)
                    sheet = wb.active
                    data = []
                    for row in sheet.iter_rows(values_only=True):
                        if any(v is not None for v in row):
                            data.append([str(v) if v is not None else "" for v in row])
                    if data and len(data) >= 1:
                        self.excel_headers = [str(h) for h in data[0]]
                        self.excel_rows = data[1:]
                        self.excel_sheet_name = f"{sheet.title or 'Questions'}"
                        self.excel_total_rows_count = len(self.excel_rows)
                        self.excel_total_cols_count = len(self.excel_headers)
                except Exception:
                    pass

    def open_qp_preview(self, test_name: str, assessment_name: str = ""):
        """Opens the Question Paper preview dialog for the given test only if actual file exists."""
        asmn_name = assessment_name or self.selected_assessment_name
        qp_fn = self.question_papers.get(asmn_name, {}).get(test_name, "")
        if not qp_fn:
            return rx.toast.warning(f"No question paper uploaded for {test_name}.")

        filepath = rx.get_upload_dir() / qp_fn
        if not filepath.exists():
            filepath = Path("uploaded_files") / qp_fn
        if not filepath.exists():
            return rx.toast.warning(f"Question paper file '{qp_fn}' not found on server.")

        self.viewing_qp_test_name = test_name
        self.viewing_qp_assessment_name = asmn_name
        self.viewing_qp_filename = qp_fn
        self.load_excel_preview_data(qp_fn, test_name)
        self.show_qp_preview_dialog = True

    def set_show_qp_preview_dialog(self, value: bool):
        self.show_qp_preview_dialog = value
        if not value:
            self.viewing_qp_test_name = ""
            self.viewing_qp_assessment_name = ""
            self.viewing_qp_filename = ""

    # ── Dashboard computed vars ───────────────────────────────────────
    @rx.var(cache=True)
    async def my_assessments(self) -> list[AssessmentDetail]:
        """Assessments assigned to this facilitator, each enriched with
        resolved candidate objects (name, emp_id, email) and structured test_items."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)

        fac_id = auth_state.facilitator_emp_id or "F001"
        cur_fac_name = auth_state.facilitator_name
        if not cur_fac_name and fac_id:
            match = next((f for f in admin_state.facilitators if f["emp_id"].lower() == fac_id.lower()), None)
            if match:
                cur_fac_name = match["name"]

        result: list[AssessmentDetail] = []
        for a in admin_state.assessments:
            # Support multi-facilitator: check facilitator_ids list first, fall back to legacy field
            assigned_ids = a.get("facilitator_ids", [])
            if not assigned_ids:
                assigned_ids = [a.get("facilitator_id", "")]
            if fac_id not in assigned_ids:
                continue
            candidate_details = [
                {"name": c["name"], "emp_id": c["emp_id"], "email": c["email"]}
                for c in admin_state.candidates
                if c["emp_id"] in a["assigned_candidates"]
            ]
            regular_tests = a.get("tests", [])
            final_test_name = a.get("final_test", "")
            all_tests_list = list(regular_tests)
            if final_test_name:
                all_tests_list.append(final_test_name)
            test_dates = a.get("test_dates", {})
            qp_dict = self.question_papers.get(a["name"], {})
            admin_qp_dict = a.get("question_papers", {})

            # Ensure saved weightages loaded
            if not self.saved_assessment_weightages:
                self.saved_assessment_weightages = self._load_saved_weightages()
            saved_w = self.saved_assessment_weightages.get(a["name"], {})
            cur_w = self.weightage_inputs.get(a["name"], {})

            # Build list of TestItem objects with dates, has_qp, and weightage
            test_items = []
            for t_name in regular_tests:
                d = test_dates.get(t_name, "")
                has_qp = bool(qp_dict.get(t_name, "") or admin_qp_dict.get(t_name, ""))
                w_val = cur_w.get(t_name, str(saved_w.get(t_name, "")))
                test_items.append({
                    "name": t_name,
                    "date": d,
                    "is_final": False,
                    "has_qp": has_qp,
                    "weightage": w_val,
                })

            if final_test_name:
                final_d = test_dates.get(final_test_name, "")
                has_qp = bool(qp_dict.get(final_test_name, "") or admin_qp_dict.get(final_test_name, ""))
                w_val = cur_w.get(final_test_name, str(saved_w.get(final_test_name, "")))
                test_items.append({
                    "name": final_test_name,
                    "date": final_d,
                    "is_final": True,
                    "has_qp": has_qp,
                    "weightage": w_val,
                })

            fac_ids = a.get("facilitator_ids", [a.get("facilitator_id", "")])
            fac_names = a.get("facilitator_names", [a.get("facilitator_name", "")])
            fac_approvals = a.get("facilitator_approvals", {})
            my_approval = fac_approvals.get(fac_id, a.get("approval_status", "approved"))

            result.append({
                "name": a["name"],
                # Multi-facilitator
                "facilitator_ids": fac_ids,
                "facilitator_names": fac_names,
                # Dynamically reflect the logged-in facilitator
                "facilitator_id": fac_id if fac_id else (fac_ids[0] if fac_ids else ""),
                "facilitator_name": cur_fac_name if cur_fac_name else (fac_names[0] if fac_names else "Facilitator"),
                "assigned_candidates": a["assigned_candidates"],
                "status": a["status"],
                "tests": regular_tests,
                "final_test": final_test_name,
                "all_tests": all_tests_list,
                "candidate_details": candidate_details,
                "approval_status": my_approval,
                "test_dates": test_dates,
                "test_items": test_items,
                "assessment_date": a.get("assessment_date", ""),
            })
        return result

    @rx.var(cache=True)
    async def my_total_candidates(self) -> int:
        """Count of unique candidates across all assessments assigned to
        this facilitator (deduplicated by emp_id)."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        unique_ids: set[str] = set()
        for a in admin_state.assessments:
            assigned_ids = a.get("facilitator_ids", [])
            if not assigned_ids:
                assigned_ids = [a.get("facilitator_id", "")]
            if fac_id in assigned_ids:
                for cid in a["assigned_candidates"]:
                    unique_ids.add(cid)
        return len(unique_ids)

    async def open_assessment(self, index: int):
        """Opens the Assessment Workspace for the clicked assessment."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        assessments = [
            a for a in admin_state.assessments
            if fac_id in a.get("facilitator_ids", [a.get("facilitator_id", "")])
        ]
        if 0 <= index < len(assessments):
            self.selected_assessment_index = index
            self.selected_assessment_name = assessments[index]["name"]
            tests = assessments[index].get("tests", [])
            final_test = assessments[index].get("final_test", "")
            self.selected_assessment_final_test = final_test
            all_t = list(tests) + ([final_test] if final_test else [])
            self.selected_test_name = all_t[0] if all_t else ""
            self.selected_evaluation_test = self.selected_test_name  # keep Evaluation tab dropdown in sync
            # Cache candidate details for sync vars (e.g. results_candidate_options)
            self._current_assessment_candidates = [
                {"name": c["name"], "emp_id": c["emp_id"]}
                for c in admin_state.candidates
                if c["emp_id"] in assessments[index].get("assigned_candidates", [])
            ]
            # Restore and dynamically balance weightage values for this assessment
            await self.sync_assessment_weightage(assessments[index]["name"])
        # Always land on the Tests tab when opening a workspace
        self.active_workspace_tab = "tests"
        return rx.redirect("/facilitator/assessment")

    async def open_assessment_tab(self, assessment_name: str, tab: str):
        """Opens the Assessment Workspace targeting a specific tab."""
        await self.open_assessment_by_name(assessment_name)
        if tab == "feedback":
            self.selected_feedback_assessment = assessment_name
            await self._sync_feedback_defaults()
            return rx.redirect("/facilitator/feedback")
        if tab in WORKSPACE_TABS:
            self.active_workspace_tab = tab
        return rx.redirect("/facilitator/assessment")

    async def open_assessment_test(self, assessment_name: str, test_name: str):
        """Opens the Assessment Workspace directly targeting a specific test."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        assessments = [
            a for a in admin_state.assessments
            if fac_id in a.get("facilitator_ids", [a.get("facilitator_id", "")])
        ]
        for i, a in enumerate(assessments):
            if a["name"] == assessment_name:
                self.selected_assessment_index = i
                self.selected_assessment_name = assessment_name
                self.selected_test_name = test_name
                self.selected_assessment_final_test = a.get("final_test", "")
                # Cache candidate details for sync vars
                self._current_assessment_candidates = [
                    {"name": c["name"], "emp_id": c["emp_id"]}
                    for c in admin_state.candidates
                    if c["emp_id"] in a.get("assigned_candidates", [])
                ]
                # Restore and dynamically balance weightage values for this assessment
                await self.sync_assessment_weightage(assessment_name)
                break
        self.active_workspace_tab = "tests"
        return rx.redirect("/facilitator/assessment")


    async def approve_assessment(self, assessment_name: str):
        """Mark the assessment as approved in AdminState for the currently logged-in facilitator."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        for i, a in enumerate(admin_state.assessments):
            if a["name"] == assessment_name:
                updated = dict(a)
                approvals = dict(updated.get("facilitator_approvals", {}))
                approvals[fac_id] = "approved"
                updated["facilitator_approvals"] = approvals
                updated["approval_status"] = "approved"
                admin_state.assessments[i] = updated
                break
        return rx.toast.success(f"Assessment '{assessment_name}' approved!")

    async def decline_assessment(self, assessment_name: str):
        """Mark the assessment as declined in AdminState for the currently logged-in facilitator."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        for i, a in enumerate(admin_state.assessments):
            if a["name"] == assessment_name:
                updated = dict(a)
                approvals = dict(updated.get("facilitator_approvals", {}))
                approvals[fac_id] = "declined"
                updated["facilitator_approvals"] = approvals
                assigned_ids = updated.get("facilitator_ids", [updated.get("facilitator_id", "")])
                if all(approvals.get(fid) == "declined" for fid in assigned_ids):
                    updated["approval_status"] = "declined"
                admin_state.assessments[i] = updated
                break
        return rx.toast.info(f"Assessment '{assessment_name}' declined.")

    @rx.var(cache=True)
    async def approved_assessments(self) -> list[AssessmentDetail]:
        """Only the assessments this facilitator has approved — shown in the sidebar."""
        all_mine = await self.my_assessments
        return [a for a in all_mine if a.get("approval_status", "pending") == "approved"]

    @rx.var(cache=True)
    async def filtered_my_assessments(self) -> list[AssessmentDetail]:
        """my_assessments filtered by assessment_search_query (case-insensitive)."""
        all_mine = await self.my_assessments
        q = self.assessment_search_query.strip().lower()
        if not q:
            return all_mine
        return [a for a in all_mine if q in a["name"].lower()]


    async def open_assessment_by_name(self, assessment_name: str):
        """Opens the Assessment Workspace by assessment name.
        Used by the sidebar so the index always maps to the full facilitator list."""
        auth_state = await self.get_state(AuthState)
        admin_state = await self.get_state(AdminState)
        fac_id = auth_state.facilitator_emp_id
        assessments = [
            a for a in admin_state.assessments
            if fac_id in a.get("facilitator_ids", [a.get("facilitator_id", "")])
        ]
        for i, a in enumerate(assessments):
            if a["name"] == assessment_name:
                self.selected_assessment_index = i
                self.selected_assessment_name = assessment_name
                tests = assessments[i].get("tests", [])
                final_test = assessments[i].get("final_test", "")
                all_t = list(tests) + ([final_test] if final_test else [])
                self.selected_test_name = all_t[0] if all_t else ""
                # Cache candidate details for sync vars
                self._current_assessment_candidates = [
                    {"name": c["name"], "emp_id": c["emp_id"]}
                    for c in admin_state.candidates
                    if c["emp_id"] in a.get("assigned_candidates", [])
                ]
                await self.sync_assessment_weightage(assessment_name)
                break
        self.active_workspace_tab = "tests"
        return rx.redirect("/facilitator/assessment")

    # ── Facilitator Test Management & Add Test Modal ─────────────────────────
    show_add_test_modal: bool = False
    new_test_type: str = "Formative"  # "Formative" | "Summative"
    new_test_name: str = ""
    new_test_date: str = ""
    new_test_description: str = ""
    suggested_formative_name: str = ""

    def set_show_add_test_modal(self, value: bool):
        self.show_add_test_modal = value

    def close_add_test_modal(self):
        self.show_add_test_modal = False

    def set_new_test_type(self, value: str):
        self.new_test_type = value
        if value == "Summative":
            if self.new_test_name.startswith("Formative") or not self.new_test_name:
                self.new_test_name = "Summative Test"
        else:
            if self.new_test_name == "Summative Test" or not self.new_test_name:
                self.new_test_name = self.suggested_formative_name or "Formative 1"

    def set_new_test_name(self, value: str):
        self.new_test_name = value

    def set_new_test_date(self, value: str):
        self.new_test_date = value

    def set_new_test_description(self, value: str):
        if len(value) <= 200:
            self.new_test_description = value

    @rx.var
    def new_test_desc_counter(self) -> str:
        return f"{len(self.new_test_description)}/200"

    async def open_add_test_modal(self):
        """Open the Add New Test modal and calculate next formative name."""
        admin_state = await self.get_state(AdminState)
        name = self.selected_assessment_name
        current_tests = []
        for a in admin_state.assessments:
            if a["name"] == name:
                current_tests = list(a.get("tests", []))
                break

        formative_nums = []
        for t in current_tests:
            if t.startswith("Formative"):
                parts = t.split()
                if len(parts) > 1 and parts[1].isdigit():
                    try:
                        formative_nums.append(int(parts[1]))
                    except ValueError:
                        pass
        next_num = max(formative_nums, default=len(current_tests)) + 1
        formative_name = f"Formative {next_num}"

        self.suggested_formative_name = formative_name
        self.new_test_type = "Formative"
        self.new_test_name = formative_name
        self.new_test_date = ""
        self.new_test_description = ""
        self.show_add_test_modal = True

    async def facilitator_add_test(self):
        """Convenience alias for opening the modal."""
        return await self.open_add_test_modal()

    async def create_new_test(self):
        """Validate and add the newly configured test to current assessment."""
        test_name = self.new_test_name.strip()
        test_date = self.new_test_date.strip()

        if not test_name:
            return rx.toast.error("Please enter a Test Name.")
        if not test_date:
            return rx.toast.error("Please select a Test Date.")

        formatted_date = test_date
        try:
            dt = datetime.strptime(test_date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d %b %Y")
        except Exception:
            pass

        admin_state = await self.get_state(AdminState)
        name = self.selected_assessment_name
        found = False
        for i, a in enumerate(admin_state.assessments):
            if a["name"] == name:
                found = True
                updated = dict(a)
                dates = dict(updated.get("test_dates", {}))
                dates[test_name] = formatted_date
                updated["test_dates"] = dates

                if self.new_test_type == "Summative":
                    updated["final_test"] = test_name
                else:
                    current_tests = list(updated.get("tests", []))
                    if test_name not in current_tests:
                        current_tests.append(test_name)
                    updated["tests"] = current_tests

                if self.new_test_description.strip():
                    descs = dict(updated.get("test_descriptions", {}))
                    descs[test_name] = self.new_test_description.strip()
                    updated["test_descriptions"] = descs

                admin_state.assessments[i] = updated
                self.selected_test_name = test_name
                break

        if not found:
            return rx.toast.error(f"Assessment '{name}' not found.")

        # Reset Overall Report lock — facilitator must re-mark assessment Complete after adding tests
        self._unmark_assessment_complete(name)
        await self.sync_assessment_weightage(name)
        self.show_add_test_modal = False
        return rx.toast.success(f"Test '{test_name}' created successfully!")

    async def facilitator_remove_test(self, test_name: str):
        """Remove a test from the currently open assessment."""
        admin_state = await self.get_state(AdminState)
        name = self.selected_assessment_name
        for i, a in enumerate(admin_state.assessments):
            if a["name"] == name:
                updated = dict(a)
                current_tests = list(updated.get("tests", []))
                final_test = updated.get("final_test", "")
                if test_name in current_tests:
                    current_tests.remove(test_name)
                    updated["tests"] = current_tests
                elif test_name == final_test:
                    updated["final_test"] = ""

                old_dates = dict(updated.get("test_dates", {}))
                old_dates.pop(test_name, None)
                updated["test_dates"] = old_dates
                admin_state.assessments[i] = updated

                remaining = list(updated.get("tests", []))
                if updated.get("final_test"):
                    remaining.append(updated["final_test"])
                self.selected_test_name = remaining[0] if remaining else ""
                break
        # Reset Overall Report lock — facilitator must re-mark assessment Complete after removing tests
        self._unmark_assessment_complete(name)
        await self.sync_assessment_weightage(name)
        return rx.toast.info(f"Test '{test_name}' removed from {name}.")

    # ── AI Evaluation Engine & Candidate Submissions State ───────────────
    is_ai_evaluating: bool = False

    ai_evaluation_done: bool = True
    selected_ai_candidate_id: str = "EMP-101"
    show_ai_detail_modal: bool = False

    # ── AI Evaluation Progress Modal State ──────────────────────────────
    show_eval_progress_modal: bool = False
    show_restart_confirm_modal: bool = False
    eval_cancelled: bool = False
    eval_progress_questions: list[dict] = []  # [{label, status}] status: pending|evaluating|completed
    eval_progress_current: int = 0  # number completed so far

    # ── Real AI Evaluation display vars (populated after run_ai_evaluation) ──
    real_ai_score_display: str = "—"
    real_ai_max_score_display: str = "—"
    real_ai_percentage_display: str = "—"
    real_ai_evaluation_date: str = "Not evaluated"
    real_ai_eval_questions: list[dict] = []
    # answer key file uploaded by facilitator for AI eval
    answer_key_uploaded_path: str = ""

    # Default AI Evaluation candidate dataset
    ai_candidates_data: dict[str, dict] = {
        "EMP-101": {
            "name": "Rohan Sharma",
            "emp_id": "EMP-101",
            "submitted_at": "Today, 10:45 AM",
            "answer_sheet_file": "Rohan_Sharma_Stage1_AnswerSheet.pdf",
            "answered_count": "5 / 5 Questions",
            "status": "AI Evaluated",
            "total_score": 92,
            "max_score": 100,
            "grade": "A+",
            "ai_confidence": "98.6%",
            "ai_summary": "Demonstrates strong mastery of IATF 16949 automotive standards and SPC process capability (Cpk > 1.33). Response demonstrates proactive containment protocol and thorough defect mitigation principles.",
            "questions_breakdown": [
                {
                    "q_num": "Q1",
                    "title": "Automotive Quality Standards",
                    "domain": "Quality Standards",
                    "marks_awarded": "20 / 20",
                    "candidate_resp": "Option B (IATF 16949:2016)",
                    "model_ans": "Option B (IATF 16949:2016)",
                    "verdict": "Correct",
                    "ai_remarks": "Accurately identified the specialized standard for automotive production.",
                },
                {
                    "q_num": "Q2",
                    "title": "Statistical Process Control (SPC)",
                    "domain": "SPC Analysis",
                    "marks_awarded": "20 / 20",
                    "candidate_resp": "Option B (Process is capable & centered)",
                    "model_ans": "Option B (Process is capable & centered)",
                    "verdict": "Correct",
                    "ai_remarks": "Precise understanding of Cpk benchmarks for manufacturing capability.",
                },
                {
                    "q_num": "Q3",
                    "title": "FMEA Defect Prevention",
                    "domain": "Risk & FMEA",
                    "marks_awarded": "20 / 20",
                    "candidate_resp": "Option B (Proactively identify failure modes)",
                    "model_ans": "Option B (Proactively identify failure modes)",
                    "verdict": "Correct",
                    "ai_remarks": "Clear comprehension of proactive quality assurance vs post-inspection.",
                },
                {
                    "q_num": "Q4",
                    "title": "Vital Few Quality Tools",
                    "domain": "Quality Tools",
                    "marks_awarded": "16 / 20",
                    "candidate_resp": "Option B (Pareto Chart)",
                    "model_ans": "Option B (Pareto Chart)",
                    "verdict": "Correct",
                    "ai_remarks": "Correctly selected Pareto chart for 80/20 root cause prioritization.",
                },
                {
                    "q_num": "Q5",
                    "title": "Production Line Troubleshooting",
                    "domain": "Troubleshooting",
                    "marks_awarded": "16 / 20",
                    "candidate_resp": "Option B (Immediate station containment)",
                    "model_ans": "Option B (Immediate station containment)",
                    "verdict": "Correct",
                    "ai_remarks": "Correct containment procedure followed to isolate suspect inventory.",
                },
            ],
        },
        "EMP-102": {
            "name": "Priya Nair",
            "emp_id": "EMP-102",
            "submitted_at": "Today, 10:52 AM",
            "answer_sheet_file": "Priya_Nair_Technical_Sheet.docx",
            "answered_count": "5 / 5 Questions",
            "status": "AI Evaluated",
            "total_score": 86,
            "max_score": 100,
            "grade": "A",
            "ai_confidence": "97.4%",
            "ai_summary": "High analytical consistency. Solid grasp of defect containment and quality tooling with minor variance in statistical formulas.",
            "questions_breakdown": [
                {"q_num": "Q1", "title": "Automotive Quality Standards", "domain": "Quality Standards", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Correct identification of standard."},
                {"q_num": "Q2", "title": "Statistical Process Control (SPC)", "domain": "SPC Analysis", "marks_awarded": "16 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Accurate Cpk interpretation."},
                {"q_num": "Q3", "title": "FMEA Defect Prevention", "domain": "Risk & FMEA", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Accurate risk prioritization methodology."},
                {"q_num": "Q4", "title": "Vital Few Quality Tools", "domain": "Quality Tools", "marks_awarded": "15 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Appropriate tool choice for 80/20 breakdown."},
                {"q_num": "Q5", "title": "Production Line Troubleshooting", "domain": "Troubleshooting", "marks_awarded": "15 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Good operational containment protocol."},
            ],
        },
        "EMP-103": {
            "name": "Amit Patel",
            "emp_id": "EMP-103",
            "submitted_at": "Today, 11:05 AM",
            "answer_sheet_file": "Amit_Patel_Stage1_Scan.pdf",
            "answered_count": "5 / 5 Questions",
            "status": "AI Evaluated",
            "total_score": 78,
            "max_score": 100,
            "grade": "B+",
            "ai_confidence": "96.1%",
            "ai_summary": "Satisfactory performance across standard manufacturing principles. Recommended refresher on statistical tolerance limits.",
            "questions_breakdown": [
                {"q_num": "Q1", "title": "Automotive Quality Standards", "domain": "Quality Standards", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Correct standard identified."},
                {"q_num": "Q2", "title": "Statistical Process Control (SPC)", "domain": "SPC Analysis", "marks_awarded": "10 / 20", "candidate_resp": "Option A", "model_ans": "Option B", "verdict": "Incorrect", "ai_remarks": "Misinterpreted Cpk > 1.33 capability threshold."},
                {"q_num": "Q3", "title": "FMEA Defect Prevention", "domain": "Risk & FMEA", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Good comprehension of failure mode mitigation."},
                {"q_num": "Q4", "title": "Vital Few Quality Tools", "domain": "Quality Tools", "marks_awarded": "14 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Correct Pareto analysis."},
                {"q_num": "Q5", "title": "Production Line Troubleshooting", "domain": "Troubleshooting", "marks_awarded": "14 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Standard containment response applied."},
            ],
        },
        "EMP-104": {
            "name": "Sneha Kulkarni",
            "emp_id": "EMP-104",
            "submitted_at": "Today, 11:15 AM",
            "answer_sheet_file": "Sneha_K_Stage1_Response.xlsx",
            "answered_count": "5 / 5 Questions",
            "status": "AI Evaluated",
            "total_score": 96,
            "max_score": 100,
            "grade": "O (Outstanding)",
            "ai_confidence": "99.2%",
            "ai_summary": "Exceptional evaluation score with flawless answers across standards, process capability calculations, and root-cause troubleshooting.",
            "questions_breakdown": [
                {"q_num": "Q1", "title": "Automotive Quality Standards", "domain": "Quality Standards", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Flawless identification of standard."},
                {"q_num": "Q2", "title": "Statistical Process Control (SPC)", "domain": "SPC Analysis", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Clear statistical capability reasoning."},
                {"q_num": "Q3", "title": "FMEA Defect Prevention", "domain": "Risk & FMEA", "marks_awarded": "20 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Exemplary FMEA risk analysis."},
                {"q_num": "Q4", "title": "Vital Few Quality Tools", "domain": "Quality Tools", "marks_awarded": "18 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Strong Pareto prioritization."},
                {"q_num": "Q5", "title": "Production Line Troubleshooting", "domain": "Troubleshooting", "marks_awarded": "18 / 20", "candidate_resp": "Option B", "model_ans": "Option B", "verdict": "Correct", "ai_remarks": "Comprehensive line quarantine actions."},
            ],
        },
    }

    def _get_question_count_from_qp(self, qp_path: Path) -> int:
        """Read the question paper Excel and return the number of question rows."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(qp_path, data_only=True)
            sheet = wb.active
            rows = [r for r in sheet.iter_rows(values_only=True) if any(v is not None for v in r)]
            # First row is header, rest are questions
            return max(0, len(rows) - 1)
        except Exception:
            return 0


    def minimize_eval_progress_modal(self):
        """Hide the modal while evaluation continues in the background."""
        self.show_eval_progress_modal = False

    def stop_ai_evaluation(self):
        """UI-ready handler to pause evaluation and save completed results."""
        return rx.toast.info("Evaluation paused. Completed results saved.")

    def resume_ai_evaluation(self):
        """UI-ready handler to continue evaluation from the next pending question."""
        return rx.toast.info("Evaluation resumed from the next pending question.")

    def open_restart_confirm_modal(self):
        """Show confirmation dialog before restarting evaluation."""
        self.show_restart_confirm_modal = True

    def close_restart_confirm_modal(self):
        """Dismiss the restart confirmation dialog."""
        self.show_restart_confirm_modal = False

    def restart_ai_evaluation(self):
        """UI-ready handler to restart evaluation after confirmation."""
        self.show_restart_confirm_modal = False
        return rx.toast.info("Evaluation restarted.")

    async def run_ai_evaluation(self):
        """Run the real AI Evaluation Engine using Azure OpenAI.
        Reads the uploaded Question Paper and the latest candidate response file.
        Falls back gracefully to mock data if files or API credentials are missing.
        """
        self.eval_cancelled = False
        self.is_ai_evaluating = True
        self.show_eval_progress_modal = False
        self.eval_progress_questions = []
        self.eval_progress_current = 0
        yield

        try:
            if _evaluate_candidate is None:
                raise ImportError("ai_evaluation_service not available")

            # Determine question paper path - strictly from uploaded question paper for this assessment + test
            qp_filename = self.question_papers.get(self.selected_assessment_name, {}).get(self.selected_test_name, "")
            if not qp_filename:
                raise FileNotFoundError(
                    f"No question paper uploaded for assessment '{self.selected_assessment_name}' "
                    f"and test '{self.selected_test_name}'. Please upload a question paper first."
                )

            qp_path = Path(rx.get_upload_dir()) / qp_filename
            if not qp_path.exists():
                qp_path = Path("uploaded_files") / qp_filename
            if not qp_path.exists():
                raise FileNotFoundError(
                    f"Uploaded question paper file '{qp_filename}' not found on server."
                )

            # Find candidate response file filtered by selected candidate + assessment + test
            raw = self.selected_evaluation_candidate
            test_name = self.selected_test_name
            asmn_name = self.selected_assessment_name
            candidate_response_path = _find_response_file_path(raw, test_name, asmn_name)
            if candidate_response_path is None:
                raise FileNotFoundError(
                    f"No response file found for candidate '{raw}' and test '{test_name}' "
                    f"in uploaded_files/candidate_responses/. "
                    f"Please ensure the candidate has submitted their test."
                )

            # ── Build progress question list from actual QP ──────────────
            q_count = await asyncio.to_thread(self._get_question_count_from_qp, qp_path)
            if q_count == 0:
                q_count = 1  # fallback: at least show 1
            self.eval_progress_questions = [
                {"label": f"Question {i + 1}", "status": "pending"}
                for i in range(q_count)
            ]
            self.eval_progress_current = 0
            self.show_eval_progress_modal = True
            yield  # show modal immediately

            # Check if separate answer key was uploaded
            ak_path = self.answer_key_uploaded_path if self.answer_key_uploaded and self.answer_key_uploaded_path else None

            # Run blocking AI evaluation in a background thread while
            # streaming per-question progress updates to the UI.
            import concurrent.futures
            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = loop.run_in_executor(executor, _evaluate_candidate, str(qp_path), str(candidate_response_path), ak_path)

            # Animate progress question-by-question while waiting for the real result
            per_q_delay = max(1.0, 4.0)  # seconds per question step shown (min 1s)
            for qi in range(q_count):
                if self.eval_cancelled:
                    future.cancel()
                    return
                # Mark current question as evaluating
                updated = list(self.eval_progress_questions)
                updated[qi] = {"label": updated[qi]["label"], "status": "evaluating"}
                self.eval_progress_questions = updated
                self.eval_progress_current = qi
                yield

                # Wait up to per_q_delay seconds, but stop as soon as future is done
                elapsed = 0.0
                step = 0.3
                while elapsed < per_q_delay:
                    if self.eval_cancelled:
                        future.cancel()
                        return
                    if future.done():
                        break
                    await asyncio.sleep(step)
                    elapsed += step

                if self.eval_cancelled:
                    future.cancel()
                    return

                # Mark as completed
                updated = list(self.eval_progress_questions)
                updated[qi] = {"label": updated[qi]["label"], "status": "completed"}
                self.eval_progress_questions = updated
                self.eval_progress_current = qi + 1
                yield

                if future.done():
                    # Fast-complete remaining questions visually
                    remaining = list(self.eval_progress_questions)
                    for rj in range(qi + 1, q_count):
                        remaining[rj] = {"label": remaining[rj]["label"], "status": "completed"}
                    self.eval_progress_questions = remaining
                    self.eval_progress_current = q_count
                    yield
                    break

            if self.eval_cancelled:
                future.cancel()
                return

            # Close progress modal as soon as all questions are visually complete
            self.show_eval_progress_modal = False
            yield

            if self.eval_cancelled:
                future.cancel()
                return

            # Await the actual result (already done or still running)
            result = await asyncio.wrap_future(future)

            # Parse summary from results
            results_list = result.get("results", [])
            summary_df = result.get("candidate_summary_df", None)

            if summary_df is not None and not summary_df.empty:
                first = summary_df.iloc[0]
                total_awarded = float(first.get("total_awarded_marks", 0))
                total_max = float(first.get("total_maximum_marks", 0))
                pct = round((total_awarded / total_max) * 100, 1) if total_max > 0 else 0
                pct_display = f"{int(pct)}%" if pct == int(pct) else f"{pct}%"
                disp_awarded = int(total_awarded) if total_awarded == int(total_awarded) else total_awarded
                disp_max = int(total_max) if total_max == int(total_max) else total_max
                self.real_ai_score_display = f"{disp_awarded} / {disp_max}"
                self.real_ai_max_score_display = str(disp_max)
                self.real_ai_percentage_display = pct_display
            elif results_list:
                total_awarded = sum(float(r.get("awarded_marks", 0)) for r in results_list)
                total_max = sum(float(r.get("maximum_marks", r.get("max_marks", 0))) for r in results_list)
                pct = round((total_awarded / total_max) * 100, 1) if total_max > 0 else 0
                pct_display = f"{int(pct)}%" if pct == int(pct) else f"{pct}%"
                disp_awarded = int(total_awarded) if total_awarded == int(total_awarded) else total_awarded
                disp_max = int(total_max) if total_max == int(total_max) else total_max
                self.real_ai_score_display = f"{disp_awarded} / {disp_max}"
                self.real_ai_max_score_display = str(disp_max)
                self.real_ai_percentage_display = pct_display

            self.real_ai_evaluation_date = datetime.now().strftime("%d %b %Y, %I:%M %p")

            # Build question-wise breakdown for UI (with per-question normalized score out of 100)
            breakdown = []
            for r in results_list:
                try:
                    q_obt = float(r.get("awarded_marks", 0) or 0)
                    q_max = float(r.get("maximum_marks", r.get("max_marks", 0)) or 0)
                    q_val = (q_obt / q_max) * 100.0 if q_max > 0 else 0.0
                    q_pct_str = f"{int(q_val)}%" if q_val == int(q_val) else f"{round(q_val, 1)}%"
                except (ValueError, TypeError):
                    q_pct_str = "0%"
                breakdown.append({
                    "q_no": str(r.get("question_no", "")),
                    "question": str(r.get("question", "")),
                    "response": str(r.get("candidate_answer", "")),
                    "ai_score": str(r.get("awarded_marks", "")),
                    "max_marks": str(r.get("maximum_marks", r.get("max_marks", ""))),
                    "score_pct": q_pct_str,
                    "justification": str(r.get("justification", "")),
                })
            self.real_ai_eval_questions = breakdown

            # Extract CO, LO, RBT analysis if available
            co_items = []
            co_df = result.get("co_analysis_df", None)
            if co_df is not None and not getattr(co_df, "empty", True):
                for _, row in co_df.iterrows():
                    val = str(row.get("co", ""))
                    pct = int(round(float(row.get("attainment_percentage", 0))))
                    co_items.append({"name": f"CO - {val}", "code": val, "score": pct})

            lo_items = []
            lo_df = result.get("lo_analysis_df", None)
            if lo_df is not None and not getattr(lo_df, "empty", True):
                for _, row in lo_df.iterrows():
                    val = str(row.get("lo", ""))
                    pct = int(round(float(row.get("attainment_percentage", 0))))
                    lo_items.append({"name": f"LO - {val}", "code": val, "score": pct})

            rbt_items = []
            rbt_df = result.get("rbt_analysis_df", None)
            if rbt_df is not None and not getattr(rbt_df, "empty", True):
                for _, row in rbt_df.iterrows():
                    val = str(row.get("rbt_level", ""))
                    pct = int(round(float(row.get("attainment_percentage", 0))))
                    rbt_items.append({"name": val, "code": val, "score": pct})

            results_df = result.get("results_df", None)
            domain_items = []
            kt_items = []
            if results_df is not None and not getattr(results_df, "empty", True):
                if "domain" in results_df.columns:
                    for d_val, grp in results_df.groupby("domain"):
                        if d_val is not None and str(d_val).strip() and str(d_val).lower() != "nan":
                            awd = float(grp["awarded_marks"].sum())
                            mx = float(grp["maximum_marks"].sum())
                            pct = int(round((awd / mx) * 100)) if mx > 0 else 0
                            domain_items.append({"name": str(d_val), "code": str(d_val), "score": pct})
                if "knowledge_type" in results_df.columns:
                    for kt_val, grp in results_df.groupby("knowledge_type"):
                        if kt_val is not None and str(kt_val).strip() and str(kt_val).lower() != "nan":
                            awd = float(grp["awarded_marks"].sum())
                            mx = float(grp["maximum_marks"].sum())
                            pct = int(round((awd / mx) * 100)) if mx > 0 else 0
                            kt_items.append({"name": str(kt_val), "code": str(kt_val), "score": pct})

            # Persist real result per candidate+test key
            key = f"{self.selected_evaluation_candidate}:{self.selected_test_name}"
            saved_results = dict(self.real_ai_results_per_candidate)
            norm_pct = round((total_awarded / total_max) * 100.0, 1) if total_max > 0 else 0.0
            saved_results[key] = {
                "score": self.real_ai_score_display,
                "marks_obtained": total_awarded,
                "max_marks": total_max,
                "normalized_score": norm_pct,
                "max_score": self.real_ai_max_score_display,
                "percentage": f"{norm_pct}%",
                "eval_date": self.real_ai_evaluation_date,
                "questions": breakdown,
                "co": co_items,
                "lo": lo_items,
                "rbt_level": rbt_items,
                "domain": domain_items,
                "knowledge_type": kt_items,
            }
            self.real_ai_results_per_candidate = saved_results

            # Update ai_candidates_data with real result for the selected candidate emp_id
            raw = self.selected_evaluation_candidate
            cand_id = raw.split("(")[-1].rstrip(")").strip() if "(" in raw else raw.strip()
            existing = dict(self.ai_candidates_data.get(cand_id, {}))
            existing["total_score"] = int(float(self.real_ai_score_display.split("/")[0].strip())) if "/" in self.real_ai_score_display else 0
            existing["ai_confidence"] = "Real AI"
            updated_data = dict(self.ai_candidates_data)
            updated_data[cand_id] = existing
            self.ai_candidates_data = updated_data

            self.is_ai_evaluating = False
            self.ai_evaluation_done = True
            yield rx.toast.success(f"AI Evaluation completed! Score: {self.real_ai_score_display} ({self.real_ai_percentage_display})")

        except FileNotFoundError as e:
            self.show_eval_progress_modal = False
            self.is_ai_evaluating = False
            self.ai_evaluation_done = True
            yield rx.toast.warning(f"File not found — using mock data. ({e})")
        except Exception as e:
            self.show_eval_progress_modal = False
            self.is_ai_evaluating = False
            self.ai_evaluation_done = True
            err_msg = str(e)[:120]
            yield rx.toast.error(f"AI Evaluation error: {err_msg}")

    def open_ai_candidate_detail(self, candidate_id: str):
        """Open the detailed AI score & feedback breakdown modal for a candidate."""
        self.selected_ai_candidate_id = candidate_id
        self.show_ai_detail_modal = True

    def set_show_ai_detail_modal(self, value: bool):
        self.show_ai_detail_modal = value

    @rx.var
    def selected_ai_candidate_data(self) -> dict:
        """Returns the active candidate's AI evaluation details."""
        return self.ai_candidates_data.get(self.selected_ai_candidate_id, self.ai_candidates_data["EMP-101"])

    @rx.var
    def selected_ai_candidate_questions(self) -> list[dict]:
        """Returns question breakdown list for the selected candidate."""
        data = self.selected_ai_candidate_data
        return data.get("questions_breakdown", []) if data else []

    @rx.var
    def average_ai_score(self) -> int:
        scores = [v["total_score"] for v in self.ai_candidates_data.values()]
        return sum(scores) // len(scores) if scores else 0

    @rx.var
    def highest_ai_score(self) -> int:
        scores = [v["total_score"] for v in self.ai_candidates_data.values()]
        return max(scores) if scores else 0

    def mock_download_results(self):
        """Mock CSV download — shows a toast."""
        return rx.toast.info("AI Evaluation Results Report downloaded (Mock CSV)!")

    # ── Results Tab Analytics State ────────────────────────────────────
    results_selected_candidate: str = "All Candidates"
    results_view_mode: str = "individual"  # "individual" or "all"
    results_active_dimension_tab: str = "co"  # "co", "lo", "knowledge_type", "domain", "rbt_level", "question_wise"
    results_selected_test: str = ""  # empty = first test / all tests; otherwise specific test name
    results_selected_analysis_test: str = ""  # specific test for Test-wise / Question-wise analysis
    results_test_wise_sub_tab: str = "co"  # "co", "lo", "knowledge_type", "domain", "rbt_level", "question_wise"
    results_search_candidate: str = ""
    show_all_questions: bool = False
    show_results_report_modal: bool = False
    show_download_pdf_modal: bool = False
    download_pdf_report_type: str = "individual"  # "individual" or "all"
    download_pdf_candidate: str = ""
    download_pdf_selected_tests: list[str] = []
    # ── Close Assessment & Facilitator Feedback Form State ────────────
    show_close_assessment_confirm_dialog: bool = False
    show_facilitator_feedback_modal: bool = False
    close_assessment_feedback_title: str = ""
    close_assessment_feedback_questions: list[dict] = []
    close_assessment_feedback_answers: dict[str, str] = {}
    # Sync cache of the current assessment's candidates — populated in open_assessment handlers
    _current_assessment_candidates: list[dict] = []

    def set_results_view_mode(self, mode: str):
        self.results_view_mode = mode
        if mode == "individual":
            if self.results_selected_candidate in ("All Candidates", ""):
                if self._current_assessment_candidates:
                    c = self._current_assessment_candidates[0]
                    self.results_selected_candidate = f"{c['name']} ({c['emp_id']})"
        else:
            self.results_selected_candidate = "All Candidates"

    def back_to_assessments(self):
        return rx.redirect("/facilitator/dashboard")

    def set_results_search_candidate(self, val: str):
        self.results_search_candidate = val

    def toggle_show_all_questions(self):
        self.show_all_questions = not self.show_all_questions

    def open_results_report_modal(self):
        self.show_results_report_modal = True

    def close_results_report_modal(self):
        self.show_results_report_modal = False

    async def open_download_pdf_modal(self):
        self.show_download_pdf_modal = True
        self.download_pdf_report_type = "individual" if self.results_view_mode == "individual" else "all"
        if not self.download_pdf_candidate or self.download_pdf_candidate == "All Candidates":
            if self.results_selected_candidate and self.results_selected_candidate != "All Candidates":
                self.download_pdf_candidate = self.results_selected_candidate
            else:
                opts = await self.results_candidate_options
                if opts:
                    self.download_pdf_candidate = opts[0]
                elif self._current_assessment_candidates:
                    c = self._current_assessment_candidates[0]
                    self.download_pdf_candidate = f"{c['name']} ({c['emp_id']})"
        tests = await self.download_pdf_test_options
        if not self.download_pdf_selected_tests and tests:
            self.download_pdf_selected_tests = [tests[0]]

    def close_download_pdf_modal(self):
        self.show_download_pdf_modal = False

    def set_show_download_pdf_modal(self, val: bool):
        self.show_download_pdf_modal = val

    async def set_download_pdf_report_type(self, rtype: str):
        self.download_pdf_report_type = rtype
        if rtype == "individual" and (not self.download_pdf_candidate or self.download_pdf_candidate == "All Candidates"):
            if self.results_selected_candidate and self.results_selected_candidate != "All Candidates":
                self.download_pdf_candidate = self.results_selected_candidate
            else:
                opts = await self.results_candidate_options
                if opts:
                    self.download_pdf_candidate = opts[0]
                elif self._current_assessment_candidates:
                    c = self._current_assessment_candidates[0]
                    self.download_pdf_candidate = f"{c['name']} ({c['emp_id']})"

    def set_download_pdf_candidate(self, cand: str):
        self.download_pdf_candidate = cand

    def toggle_download_pdf_test(self, test_name: str):
        if test_name in self.download_pdf_selected_tests:
            self.download_pdf_selected_tests = [t for t in self.download_pdf_selected_tests if t != test_name]
        else:
            self.download_pdf_selected_tests = self.download_pdf_selected_tests + [test_name]

    def download_pdf_modal_submit(self):
        self.show_download_pdf_modal = False
        return rx.toast.info("Download PDF submitted (UI action).")

    def open_close_assessment_dialog(self):
        self.show_close_assessment_confirm_dialog = True

    def close_close_assessment_dialog(self):
        self.show_close_assessment_confirm_dialog = False

    def set_show_close_assessment_confirm_dialog(self, val: bool):
        self.show_close_assessment_confirm_dialog = val

    async def confirm_close_assessment(self):
        self.show_close_assessment_confirm_dialog = False
        admin_state = await self.get_state(AdminState)
        asmn = self.selected_assessment_name

        saved = admin_state.facilitator_saved_forms.get(asmn)
        if saved and saved.get("questions"):
            self.close_assessment_feedback_title = saved.get("title", f"Facilitator Feedback Form - {asmn}")
            self.close_assessment_feedback_questions = [dict(q) for q in saved.get("questions", [])]
        elif admin_state.facilitator_form_questions:
            self.close_assessment_feedback_title = admin_state.facilitator_form_title or f"Facilitator Feedback Form - {asmn}"
            self.close_assessment_feedback_questions = [dict(q) for q in admin_state.facilitator_form_questions]
        else:
            self.close_assessment_feedback_title = f"Facilitator Feedback Form - {asmn}"
            self.close_assessment_feedback_questions = [
                {
                    "id": "fq_1",
                    "text": "How effectively did this assessment evaluate the intended competencies?",
                    "required": True,
                },
                {
                    "id": "fq_2",
                    "text": "Were there any technical issues, ambiguities, or evaluation discrepancies encountered?",
                    "required": True,
                },
                {
                    "id": "fq_3",
                    "text": "Provide any recommendations or feedback on overall candidate performance and assessment flow.",
                    "required": False,
                },
            ]

        self.close_assessment_feedback_answers = {q["id"]: "" for q in self.close_assessment_feedback_questions}
        self.show_facilitator_feedback_modal = True

    def close_facilitator_feedback_modal(self):
        self.show_facilitator_feedback_modal = False

    def set_show_facilitator_feedback_modal(self, val: bool):
        self.show_facilitator_feedback_modal = val

    def set_close_assessment_feedback_answer(self, qid: str, value: str):
        answers = dict(self.close_assessment_feedback_answers)
        answers[qid] = value
        self.close_assessment_feedback_answers = answers

    def submit_facilitator_feedback_modal(self):
        self.show_facilitator_feedback_modal = False
        return rx.toast.success("Feedback submitted successfully. Assessment closed.")

    @rx.var(cache=True)
    async def download_pdf_test_options(self) -> list[str]:
        """Dynamically list all tests actually created for the selected assessment."""
        asmn = self.selected_assessment_name
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        names = []
        if match:
            for t in match.get("test_items", []):
                t_name = t.get("name", "")
                if t_name and t_name not in names:
                    names.append(t_name)
        if not names:
            tests = await self.results_assessment_tests
            for t in tests:
                t_name = t.get("name", "")
                if t_name and t_name not in names:
                    names.append(t_name)
        return names

    def view_individual_candidate_results(self, name: str, emp_id: str):
        self.results_selected_candidate = f"{name} ({emp_id})"
        self.results_view_mode = "individual"

    def results_report_print(self):
        return rx.call_script("if (window.printReportDocument) window.printReportDocument(); else window.print();")

    def results_report_download_pdf(self):
        return rx.call_script("if (window.printReportDocument) window.printReportDocument(); else window.print();")

    def set_results_selected_candidate(self, candidate_name: str):
        self.results_selected_candidate = candidate_name

    def set_results_dimension_tab(self, tab_key: str):
        self.results_active_dimension_tab = tab_key

    def set_results_selected_test(self, test_name: str):
        """Update the results test filter and also sync selected_test_name."""
        if test_name in ("All Tests (Overall)", ""):
            self.results_selected_test = ""
            self.selected_test_name = ""
        else:
            self.results_selected_test = test_name
            self.selected_test_name = test_name

    def set_results_selected_analysis_test(self, test_name: str):
        self.results_selected_analysis_test = test_name

    def set_results_test_wise_sub_tab(self, sub_tab: str):
        self.results_test_wise_sub_tab = sub_tab

    @rx.var
    async def results_effective_analysis_test(self) -> str:
        if self.results_selected_analysis_test:
            return self.results_selected_analysis_test
        tests = await self.results_assessment_tests
        if tests:
            return tests[0]["name"]
        return ""

    @rx.var
    async def results_effective_test(self) -> str:
        if self.results_selected_test:
            return self.results_selected_test
        tests = await self.results_assessment_tests
        if tests:
            return tests[0]["name"]
        return ""

    @rx.var
    def results_selected_test_display(self) -> str:
        return self.results_selected_test if self.results_selected_test else "All Tests (Overall)"

    @rx.var(cache=True)
    async def results_candidate_options(self) -> list[str]:
        """Derive Results candidate dropdown dynamically from the actual candidates assigned to the currently selected assessment."""
        options = []
        admin_state = await self.get_state(AdminState)

        # 1. Match assessment by selected_assessment_name, or fall back to first assessment in admin_state
        target_name = self.selected_assessment_name.strip().lower()
        target_a = None
        for a in admin_state.assessments:
            if target_name and a.get("name", "").strip().lower() == target_name:
                target_a = a
                break
        if target_a is None and admin_state.assessments:
            target_a = admin_state.assessments[0]

        if target_a:
            # Candidate IDs assigned to this assessment
            assigned_ids = target_a.get("assigned_candidates", [])

            # Map of candidate ID -> Candidate Name from admin_state.candidates
            cand_map = {c["emp_id"]: c["name"] for c in admin_state.candidates if "emp_id" in c and "name" in c}

            # Fallback to SHARED_CANDIDATES
            from ai_hybrid_evaluator.models.models import SHARED_CANDIDATES
            for c in SHARED_CANDIDATES:
                if c["emp_id"] not in cand_map:
                    cand_map[c["emp_id"]] = c["name"]

            for cid in assigned_ids:
                cname = cand_map.get(cid, cid)
                label = f"{cname} ({cid})"
                if label not in options:
                    options.append(label)

            # Also check if target_a has candidate_details or candidates dicts directly
            for c in target_a.get("candidate_details", []):
                label = f"{c['name']} ({c['emp_id']})"
                if label not in options:
                    options.append(label)

        # Also include any evaluated candidates from real_ai_results_per_candidate
        for key in self.real_ai_results_per_candidate.keys():
            cand_part = key.split(":")[0].strip()
            if cand_part and cand_part != "All Candidates" and cand_part not in options:
                options.append(cand_part)

        return options

    @rx.var(cache=True)
    async def results_effective_candidate(self) -> str:
        if self.results_view_mode == "individual":
            if self.results_selected_candidate and self.results_selected_candidate != "All Candidates":
                return self.results_selected_candidate
            opts = await self.results_candidate_options
            return opts[0] if opts else "Priya Sharma (CAND-2031)"
        return "All Candidates"

    @rx.var(cache=True)
    async def results_effective_candidate_name(self) -> str:
        cand = await self.results_effective_candidate
        return cand.split("(")[0].strip() if "(" in cand else cand

    @rx.var(cache=True)
    async def results_test_options(self) -> list[str]:
        """List of test names in the selected assessment for the Results test dropdown."""
        options = ["All Tests (Overall)"]
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == self.selected_assessment_name:
                for t in a.get("test_items", []):
                    if t["name"] not in options:
                        options.append(t["name"])
                break
        saved_w = self.saved_assessment_weightages.get(self.selected_assessment_name, {})
        for t_name in saved_w.keys():
            if t_name not in options:
                options.append(t_name)
        for key in self.real_ai_results_per_candidate.keys():
            parts = key.split(":")
            if len(parts) > 1:
                t_name = parts[1].strip()
                if t_name and t_name not in options:
                    options.append(t_name)
        return options

    @rx.var
    def results_eval_status(self) -> str:
        """'Evaluated' or 'Not Evaluated' for the selected candidate + test combo."""
        cand = self.results_selected_candidate
        test = self.results_selected_test or self.selected_test_name
        if cand == "All Candidates" or not cand or not test:
            return ""
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        for key in self.real_ai_results_per_candidate:
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if t_part == test and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower()):
                return "Evaluated"
        return "Not Evaluated"

    @rx.var
    def results_eval_date(self) -> str:
        """Submission / eval date for the selected candidate + test."""
        cand = self.results_selected_candidate
        test = self.results_selected_test or self.selected_test_name
        if cand == "All Candidates" or not cand or not test:
            return ""
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if t_part == test and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower()):
                return val.get("eval_date", "")
        return ""

    @rx.var
    def results_question_analysis_items(self) -> list[dict]:
        """Question-wise breakdown for the selected candidate + test, or average question performance across all candidates for the selected test.
        Each item: q_no, q_display, question, marks_obtained, max_marks, score_pct_num, score_pct, remarks, bar_pct, r_color, r_bg, justification."""
        is_ind = (self.results_view_mode == "individual")
        cand = self.results_selected_candidate

        # In individual mode, ensure a specific candidate is targeted
        if is_ind and (not cand or cand == "All Candidates"):
            if self._current_assessment_candidates:
                first_c = self._current_assessment_candidates[0]
                cand = f"{first_c['name']} ({first_c['emp_id']})"
            else:
                for key in self.real_ai_results_per_candidate.keys():
                    cand = key.split(":")[0].strip()
                    break

        test = (self.results_selected_analysis_test or self.results_selected_test or self.selected_test_name or "").strip()
        if not test or test == "All Tests (Overall)":
            saved_w = self.saved_assessment_weightages.get(self.selected_assessment_name, {})
            if saved_w:
                test = list(saved_w.keys())[0]
            if not test:
                for key in self.real_ai_results_per_candidate.keys():
                    parts = key.split(":")
                    if len(parts) > 1 and parts[1].strip():
                        test = parts[1].strip()
                        break

        if not test:
            return []

        pass_pct = self.results_pass_percentage

        # ── All Candidates Mode: Average score for each question across candidates ──
        if not is_ind or cand in ("All Candidates", ""):
            q_agg: dict[str, dict] = {}
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                t_part = parts[1].strip() if len(parts) > 1 else ""
                if t_part.lower() == test.lower():
                    for i, q in enumerate(val.get("questions", []), 1):
                        q_raw = str(q.get("q_no", i))
                        q_key = q_raw.lstrip("Q") if q_raw.startswith("Q") and q_raw[1:].isdigit() else q_raw
                        q_disp = f"Q{q_key}" if q_key.isdigit() else q_key
                        if q_key not in q_agg:
                            try:
                                mx = float(q.get("max_marks", q.get("maximum_marks", 0)) or 0)
                            except (ValueError, TypeError):
                                mx = 0.0
                            q_agg[q_key] = {
                                "question": str(q.get("question", f"Question {q_key}")),
                                "marks": [],
                                "max": mx,
                                "q_no": q_key,
                                "q_display": q_disp,
                            }
                        try:
                            obt = float(q.get("ai_score", q.get("awarded_marks", 0)) or 0)
                        except (ValueError, TypeError):
                            obt = 0.0
                        q_agg[q_key]["marks"].append(obt)

            items = []
            for q_key, info in q_agg.items():
                m_list = info["marks"]
                mx = info["max"]
                avg_obt = round(sum(m_list) / len(m_list), 1) if m_list else 0.0
                pct = round((avg_obt / mx) * 100, 1) if mx > 0 else 0.0
                pct_int = int(pct) if pct == int(pct) else pct
                pct_str = f"{pct_int}%"
                if pct >= max(85, pass_pct + 15):
                    remarks = "Excellent"
                    r_color = "#059669"
                    r_bg = "#ECFDF5"
                elif pct >= pass_pct:
                    remarks = "Good"
                    r_color = "#2563EB"
                    r_bg = "#EFF6FF"
                elif pct >= max(0, pass_pct - 15):
                    remarks = "Average"
                    r_color = "#D97706"
                    r_bg = "#FFFBEB"
                else:
                    remarks = "Needs Work"
                    r_color = "#DC2626"
                    r_bg = "#FEF2F2"
                items.append({
                    "q_no": info["q_no"],
                    "q_display": info["q_display"],
                    "question": info["question"],
                    "marks_obtained": str(avg_obt),
                    "max_marks": str(int(mx) if mx == int(mx) else mx),
                    "score_pct": pct_str,
                    "score_pct_num": pct,
                    "remarks": remarks,
                    "r_color": r_color,
                    "r_bg": r_bg,
                    "bar_pct": pct,
                    "justification": "",
                })
            return items

        # ── Individual Candidate Mode: Single candidate's question results ──
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if t_part.lower() == test.lower() and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower() or cand == c_part):
                items = []
                for i, q in enumerate(val.get("questions", []), 1):
                    try:
                        obt = float(q.get("ai_score", q.get("awarded_marks", 0)) or 0)
                        mx = float(q.get("max_marks", q.get("maximum_marks", 0)) or 0)
                        pct = round((obt / mx) * 100, 1) if mx > 0 else 0.0
                    except (ValueError, TypeError):
                        obt, mx, pct = 0.0, 0.0, 0.0
                    pct_int = int(pct) if pct == int(pct) else pct
                    pct_str = f"{pct_int}%"
                    if pct >= max(85, pass_pct + 15):
                        remarks = "Excellent"
                        r_color = "#059669"
                        r_bg = "#ECFDF5"
                    elif pct >= pass_pct:
                        remarks = "Good"
                        r_color = "#2563EB"
                        r_bg = "#EFF6FF"
                    elif pct >= max(0, pass_pct - 15):
                        remarks = "Average"
                        r_color = "#D97706"
                        r_bg = "#FFFBEB"
                    else:
                        remarks = "Needs Work"
                        r_color = "#DC2626"
                        r_bg = "#FEF2F2"

                    q_raw = str(q.get("q_no", i))
                    q_disp = f"Q{q_raw}" if q_raw.isdigit() else (q_raw if q_raw.startswith("Q") else f"Q{q_raw}")
                    q_num = q_raw.lstrip("Q") if q_raw.startswith("Q") and q_raw[1:].isdigit() else q_raw

                    raw_just = q.get("justification") or q.get("feedback") or q.get("ai_feedback") or q.get("reasoning") or q.get("remarks") or ""
                    justification = str(raw_just).strip() if raw_just else "—"

                    items.append({
                        "q_no": q_num,
                        "q_display": q_disp,
                        "question": str(q.get("question", f"Question {i}")),
                        "marks_obtained": str(int(obt) if obt == int(obt) else obt),
                        "max_marks": str(int(mx) if mx == int(mx) else mx),
                        "score_pct": pct_str,
                        "score_pct_num": pct,
                        "remarks": remarks,
                        "r_color": r_color,
                        "r_bg": r_bg,
                        "bar_pct": pct,
                        "justification": justification,
                    })
                return items
        return []

    @rx.var
    def results_performance_summary(self) -> dict:
        """Performance summary card data: total_questions, marks_str, normalized_str, status."""
        cand = self.results_selected_candidate
        test = self.results_selected_test or self.selected_test_name
        pass_pct = self.results_pass_percentage
        if cand == "All Candidates" or not cand or not test:
            data = self.current_results_data
            if not data:
                return {"total_questions": "—", "marks_str": "—", "normalized_str": "—", "status": "—", "status_color": "#475467"}
            score = data.get("overall_score", 0)
            return {
                "total_questions": "—",
                "marks_str": "—",
                "normalized_str": f"{score}%",
                "status": "Passed" if score >= pass_pct else "Failed",
                "status_color": "#059669" if score >= pass_pct else "#DC2626",
            }
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if t_part == test and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower()):
                obt = val.get("marks_obtained", 0)
                mx = val.get("max_marks", 0)
                norm = val.get("normalized_score", 0)
                questions = val.get("questions", [])
                norm_str = f"{int(norm)}%" if norm == int(norm) else f"{norm}%"
                obt_d = int(obt) if isinstance(obt, float) and obt == int(obt) else obt
                mx_d = int(mx) if isinstance(mx, float) and mx == int(mx) else mx
                pass_thresh = self.get_test_pass_percentage(test)
                passed = norm >= pass_thresh
                return {
                    "total_questions": str(len(questions)),
                    "marks_str": f"{obt_d} / {mx_d}",
                    "normalized_str": norm_str,
                    "status": "Passed" if passed else "Failed",
                    "status_color": "#059669" if passed else "#DC2626",
                }
        return {"total_questions": "—", "marks_str": "—", "normalized_str": "—", "status": "—", "status_color": "#475467"}

    @rx.var
    def current_results_data(self) -> dict:
        """Build results data exclusively from real AI evaluation results.
        Overall Assessment Score = sum(normalized_score * weightage / 100) for each test.
        Falls back to simple average when no weightage is configured.
        Returns an empty dict if no real data exists for the selection."""
        cand = self.results_selected_candidate
        final_test_name = self.selected_assessment_final_test
        asmn = self.selected_assessment_name

        # Load saved weightages for this assessment
        saved_w: dict[str, int] = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        use_weightage = (total_w == 100 and bool(saved_w))

        def _weighted_score(test_name: str, norm_score: float) -> float:
            """Return weighted contribution of a test score."""
            if use_weightage and test_name in saved_w:
                return round(norm_score * saved_w[test_name] / 100.0, 2)
            return norm_score  # fallback: treat each test equally

        if cand == "All Candidates":
            # Aggregate across all real results for this assessment + selected test
            all_scores = []
            test_scores: dict[str, list] = {}
            co_agg: dict[str, list] = {}
            lo_agg: dict[str, list] = {}
            rbt_agg: dict[str, list] = {}
            domain_agg: dict[str, list] = {}
            kt_agg: dict[str, list] = {}

            # Filter by selected analysis test when user has chosen one from the selector
            target_test = (self.results_selected_analysis_test or self.results_selected_test or "").strip()
            for key, res in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                test_name = parts[1].strip() if len(parts) > 1 else ""
                # Filter by selected test if test_wise is active
                if target_test and test_name and target_test != test_name:
                    continue

                # Normalized Score = (Marks Obtained / Max Marks) * 100
                norm_score = self._calculate_normalized_score(res)
                score_val = int(round(norm_score))

                all_scores.append(score_val)
                test_scores.setdefault(test_name or (target_test or "Test"), []).append(score_val)

                for item in res.get("co", []):
                    co_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in res.get("lo", []):
                    lo_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in res.get("rbt_level", []):
                    rbt_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in res.get("domain", []):
                    domain_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in res.get("knowledge_type", []):
                    kt_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))

            if not all_scores:
                return {}  # No real data — UI will show empty state

            passed = 0
            for t, v in test_scores.items():
                p_thresh = self.get_test_pass_percentage(t)
                passed += sum(1 for s in v if s >= p_thresh)

            # Final test average if available, else cohort average
            final_scores = test_scores.get(final_test_name, []) if final_test_name else []
            final_avg = int(round(sum(final_scores) / len(final_scores))) if final_scores else int(round(sum(all_scores) / len(all_scores)))

            # Compute per-test averages and apply weightage
            avg_weighted_total = 0.0
            tests_bar = []
            for t, v in test_scores.items():
                t_avg = int(round(sum(v) / len(v)))
                t_weighted = _weighted_score(t, float(t_avg))
                avg_weighted_total += t_weighted if use_weightage else 0.0
                tests_bar.append({"name": t, "score": t_avg, "is_final": (t == final_test_name)})

            avg = int(round(avg_weighted_total)) if use_weightage else int(round(sum(all_scores) / len(all_scores)))

            co_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in co_agg.items()]
            lo_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in lo_agg.items()]
            rbt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in rbt_agg.items()]
            domain_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in domain_agg.items()]
            kt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in kt_agg.items()]

            return {
                "overall_score": avg,
                "final_test_score": final_avg,
                "passing_rate": f"{int(passed / len(all_scores) * 100)}%",
                "passing_count": f"{passed} of {len(all_scores)} Candidate(s) Passed",
                "tests": tests_bar,
                "co": co_items,
                "lo": lo_items,
                "knowledge_type": kt_items,
                "domain": domain_items,
                "rbt_level": rbt_items,
                "insight_diff": 0,
                "insight_start": "",
                "insight_end": f"Cohort Average ({avg}%)",
                "use_weightage": use_weightage,
                "saved_weightages": dict(saved_w),
            }
        else:
            # Per-candidate: find actual evaluation results for this candidate + selected assessment + test
            # Filter by selected analysis test when user has chosen one from the selector
            target_test = (self.results_selected_analysis_test or self.results_selected_test or "").strip()
            if self.results_view_mode == "individual" and (cand in ("All Candidates", "") or not cand):
                if self._current_assessment_candidates:
                    first_c = self._current_assessment_candidates[0]
                    cand = f"{first_c['name']} ({first_c['emp_id']})"
            cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
            cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()

            matched_tests: dict[str, dict] = {}
            for key, res in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                cand_part = parts[0].strip()
                test_part = parts[1].strip() if len(parts) > 1 else ""

                # When a test is selected, match test strictly
                if target_test and test_part and target_test != test_part:
                    continue

                part_id = cand_part.split("(")[-1].rstrip(")").strip() if "(" in cand_part else cand_part
                part_name = cand_part.split("(")[0].strip() if "(" in cand_part else cand_part

                if (cand_id and cand_id == part_id) or (cand_name and cand_name.lower() == part_name.lower()) or (cand.strip() == cand_part):
                    matched_tests[test_part or target_test or "Test"] = res

            if not matched_tests:
                return {}  # Candidate has no evaluation result for this test -> show No Results Available

            tests_bar = []
            co_agg = {}
            lo_agg = {}
            rbt_agg = {}
            domain_agg = {}
            kt_agg = {}
            # For test breakdown shown in results tab
            test_breakdown = []

            weighted_sum = 0.0
            norm_scores_simple = []

            for t_name, m_res in matched_tests.items():
                norm_score = self._calculate_normalized_score(m_res)
                norm_score_round = round(norm_score, 1)
                score_val = int(round(norm_score))
                norm_scores_simple.append(score_val)

                t_weightage = saved_w.get(t_name, 0) if use_weightage else 0
                weighted = round(norm_score_round * t_weightage / 100.0, 1) if use_weightage else 0.0

                if use_weightage:
                    weighted_sum += weighted

                marks_obt = m_res.get("marks_obtained", "—")
                max_m = m_res.get("max_marks", "—")

                norm_str = f"{int(norm_score_round)}%" if norm_score_round == int(norm_score_round) else f"{norm_score_round}%"
                weighted_str = f"{weighted:.1f}" if use_weightage else "—"
                marks_str = f"{marks_obt} / {max_m}"
                weightage_str = f"{t_weightage}%" if use_weightage else "—"

                test_breakdown.append({
                    "name": t_name,
                    "is_final": (t_name == final_test_name),
                    "marks_obtained": str(marks_obt),
                    "max_marks": str(max_m),
                    "marks_str": marks_str,
                    "norm_score_str": norm_str,
                    "weightage": str(t_weightage) if use_weightage else "—",
                    "weightage_str": weightage_str,
                    "weighted_score_str": weighted_str,
                    "norm_score_val": score_val,
                })
                tests_bar.append({
                    "name": t_name,
                    "score": score_val,
                    "is_final": (t_name == final_test_name),
                })
                for item in m_res.get("co", []):
                    co_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in m_res.get("lo", []):
                    lo_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in m_res.get("rbt_level", []):
                    rbt_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in m_res.get("domain", []):
                    domain_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))
                for item in m_res.get("knowledge_type", []):
                    kt_agg.setdefault(item.get("name", ""), []).append(item.get("score", 0))

            if use_weightage:
                avg_score = int(round(weighted_sum))
                overall_score_str = f"{round(weighted_sum, 1)}"
            else:
                avg_score = int(round(sum(norm_scores_simple) / len(norm_scores_simple))) if norm_scores_simple else 0
                overall_score_str = str(avg_score)

            final_s = None
            if final_test_name and final_test_name in matched_tests:
                final_s = int(round(self._calculate_normalized_score(matched_tests[final_test_name])))
            final_score_val = final_s if final_s is not None else avg_score

            co_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in co_agg.items()]
            lo_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in lo_agg.items()]
            rbt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in rbt_agg.items()]
            domain_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in domain_agg.items()]
            kt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in kt_agg.items()]

            target_test = self.selected_test_name.strip()
            if target_test:
                pass_pct_val = self.get_test_pass_percentage(target_test)
            elif matched_tests and len(matched_tests) == 1:
                pass_pct_val = self.get_test_pass_percentage(list(matched_tests.keys())[0])
            else:
                pass_pct_val = self.get_assessment_overall_pass_percentage()

            return {
                "overall_score": avg_score,
                "overall_score_str": overall_score_str,
                "final_test_score": final_score_val,
                "passing_rate": "100%" if avg_score >= pass_pct_val else "0%",
                "passing_count": "Passed" if avg_score >= pass_pct_val else "Failed",
                "tests": tests_bar,
                "test_breakdown": test_breakdown,
                "co": co_items,
                "lo": lo_items,
                "knowledge_type": kt_items,
                "domain": domain_items,
                "rbt_level": rbt_items,
                "insight_diff": 0,
                "insight_start": "",
                "insight_end": f"{cand} ({overall_score_str}%)",
                "use_weightage": use_weightage,
                "saved_weightages": dict(saved_w),
            }


    @rx.var
    def results_pass_percentage(self) -> int:
        """Dynamic pass percentage for the selected test or overall assessment, read from saved weightages/configuration."""
        target_test = (self.results_selected_test or self.selected_test_name).strip()
        asmn = self.selected_assessment_name
        if target_test:
            val = self.get_test_pass_percentage(target_test, asmn)
        else:
            val = self.get_assessment_overall_pass_percentage(asmn)
        return int(round(val))

    @rx.var
    def results_pass_percentage_str(self) -> str:
        return f"{self.results_pass_percentage}%"

    @rx.var
    def results_pass_line_top(self) -> str:
        pct = max(0, min(100, self.results_pass_percentage))
        return f"{100 - pct}%"

    @rx.var
    def results_pass_badge_top(self) -> str:
        pct = max(0, min(100, self.results_pass_percentage))
        return f"calc({100 - pct}% - 14px)"

    @rx.var
    def results_pass_line_bottom(self) -> str:
        pct = max(0, min(100, self.results_pass_percentage))
        return f"{pct}%"

    @rx.var
    def results_is_passing(self) -> bool:
        return self.current_results_data.get("overall_score", 0) >= self.results_pass_percentage

    @rx.var
    def results_has_data(self) -> bool:
        """True only when real evaluation data exists for the current selection."""
        return bool(self.current_results_data)

    @rx.var
    def results_overall_score_val(self) -> str:
        return str(self.current_results_data.get("overall_score", 0))

    @rx.var
    def results_final_test_score_val(self) -> str:
        return str(self.current_results_data.get("final_test_score", 0))

    @rx.var
    def results_overall_score_pct_str(self) -> str:
        return f"{self.current_results_data.get('overall_score', 0)}%"

    @rx.var
    def results_final_test_score_pct_str(self) -> str:
        return f"{self.current_results_data.get('final_test_score', 0)}%"

    @rx.var
    def results_passing_rate_val(self) -> str:
        return str(self.current_results_data.get("passing_rate", "N/A"))

    @rx.var
    def results_passing_count_val(self) -> str:
        return str(self.current_results_data.get("passing_count", "No results yet"))

    @rx.var
    def results_insight_diff_val(self) -> int:
        return int(self.current_results_data.get("insight_diff", 0))

    @rx.var
    def results_insight_start_val(self) -> str:
        return str(self.current_results_data.get("insight_start", ""))

    @rx.var
    def results_insight_end_val(self) -> str:
        return str(self.current_results_data.get("insight_end", ""))

    @rx.var
    def results_chart_title(self) -> str:
        tab = self.results_active_dimension_tab
        cand = self.results_selected_candidate
        if tab == "overall":
            return f"Overall Performance ({cand})"
        elif tab == "co":
            return f"Course Outcomes (CO) - Attainment ({cand})"
        elif tab == "lo":
            return f"Learning Outcomes (LO) - Attainment ({cand})"
        elif tab == "knowledge_type":
            return f"Knowledge Type Proficiency ({cand})"
        elif tab == "domain":
            return f"Domain & Topic Competency ({cand})"
        elif tab == "rbt_level":
            return f"Revised Bloom's Taxonomy (RBT) Level ({cand})"
        elif tab == "question_wise":
            test = (self.results_selected_analysis_test or self.results_selected_test or "").strip()
            test_str = f" - {test}" if test else ""
            return f"Question-wise Analysis{test_str} ({cand})"
        return f"Performance Analysis ({cand})"

    @rx.var
    def results_active_dimension_summary(self) -> dict:
        """Returns summary stats for the currently active dimension tab:
        total_label, total_val, passing_label, passing_val, avg_label, avg_val, status, is_passed, info_text."""
        tab = self.results_active_dimension_tab
        if tab == "test_wise":
            tab = self.results_test_wise_sub_tab
        pass_pct = self.results_pass_percentage

        if tab == "overall":
            items = self.results_tests_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = self.current_results_data.get("overall_score", 0)
            status = "Passed" if avg >= pass_pct else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total Tests",
                "total_val": str(total if total > 0 else 1),
                "passing_label": f"Tests ≥ {pass_pct}%",
                "passing_val": str(above if total > 0 else (1 if avg >= pass_pct else 0)),
                "avg_label": "Overall Score",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"Overall performance is calculated based on evaluated tests and configured weightages. Pass mark is set to {pass_pct}%.",
            }
        elif tab == "co":
            items = self.results_co_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = int(round(sum(float(x.get("score", 0)) for x in items) / total)) if total > 0 else 0
            status = "Passed" if (avg >= pass_pct and total > 0) else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total COs",
                "total_val": str(total),
                "passing_label": f"COs ≥ {pass_pct}%",
                "passing_val": str(above),
                "avg_label": "Average CO Attainment",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"CO attainment is calculated based on the mapped questions and their configured weightages. Pass mark is set to {pass_pct}%.",
            }
        elif tab == "lo":
            items = self.results_lo_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = int(round(sum(float(x.get("score", 0)) for x in items) / total)) if total > 0 else 0
            status = "Passed" if (avg >= pass_pct and total > 0) else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total LOs",
                "total_val": str(total),
                "passing_label": f"LOs ≥ {pass_pct}%",
                "passing_val": str(above),
                "avg_label": "Average LO Attainment",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"LO attainment is calculated based on the mapped questions and their configured weightages. Pass mark is set to {pass_pct}%.",
            }
        elif tab == "knowledge_type":
            items = self.results_kt_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = int(round(sum(float(x.get("score", 0)) for x in items) / total)) if total > 0 else 0
            status = "Passed" if (avg >= pass_pct and total > 0) else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total Types",
                "total_val": str(total),
                "passing_label": f"Types ≥ {pass_pct}%",
                "passing_val": str(above),
                "avg_label": "Average Proficiency",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"Knowledge Type proficiency is calculated from evaluated question mapping. Pass mark is set to {pass_pct}%.",
            }
        elif tab == "domain":
            items = self.results_domain_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = int(round(sum(float(x.get("score", 0)) for x in items) / total)) if total > 0 else 0
            status = "Passed" if (avg >= pass_pct and total > 0) else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total Domains",
                "total_val": str(total),
                "passing_label": f"Domains ≥ {pass_pct}%",
                "passing_val": str(above),
                "avg_label": "Average Competency",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"Domain competency is calculated from evaluated question domain mappings. Pass mark is set to {pass_pct}%.",
            }
        elif tab == "rbt_level":
            items = self.results_rbt_items
            total = len(items)
            above = sum(1 for x in items if float(x.get("score", 0)) >= pass_pct)
            avg = int(round(sum(float(x.get("score", 0)) for x in items) / total)) if total > 0 else 0
            status = "Passed" if (avg >= pass_pct and total > 0) else "Failed"
            is_passed = (status == "Passed")
            return {
                "total_label": "Total RBT Levels",
                "total_val": str(total),
                "passing_label": f"Levels ≥ {pass_pct}%",
                "passing_val": str(above),
                "avg_label": "Average RBT Score",
                "avg_val": f"{avg}%",
                "status": status,
                "is_passed": is_passed,
                "info_text": f"RBT level performance reflects cognitive complexity mapping. Pass mark is set to {pass_pct}%.",
            }
        return {
            "total_label": "Total Items",
            "total_val": "0",
            "passing_label": f"Items ≥ {pass_pct}%",
            "passing_val": "0",
            "avg_label": "Average Score",
            "avg_val": "0%",
            "status": "—",
            "is_passed": False,
            "info_text": f"Pass mark is set to {pass_pct}%.",
        }

    @rx.var
    def results_tests_items(self) -> list[dict]:
        return self.current_results_data.get("tests", [])

    @rx.var
    def results_test_breakdown(self) -> list[dict]:
        """Per-test breakdown (marks, normalized score, weightage, weighted score) for selected candidate."""
        return self.current_results_data.get("test_breakdown", [])

    @rx.var
    def results_has_breakdown(self) -> bool:
        """True when a specific candidate is selected and has test breakdown entries."""
        return bool(self.results_test_breakdown)

    @rx.var
    def results_current_dimension_items(self) -> list[dict]:
        tab = self.results_active_dimension_tab
        if tab == "test_wise":
            tab = self.results_test_wise_sub_tab
        data = self.current_results_data
        if tab == "co":
            return data.get("co", [])
        elif tab == "lo":
            return data.get("lo", [])
        elif tab == "knowledge_type":
            return data.get("knowledge_type", [])
        elif tab == "domain":
            return data.get("domain", [])
        elif tab == "rbt_level":
            return data.get("rbt_level", [])
        # Overall tab:
        tests = data.get("tests", [])
        if tests:
            return tests
        score = data.get("overall_score", 0)
        target_test = (self.results_selected_test or self.selected_test_name or "Overall").strip()
        return [{"name": target_test, "score": score}]

    @rx.var
    def results_co_items(self) -> list[dict]:
        return self.current_results_data.get("co", [])

    @rx.var
    def results_lo_items(self) -> list[dict]:
        return self.current_results_data.get("lo", [])

    @rx.var
    def results_kt_items(self) -> list[dict]:
        return self.current_results_data.get("knowledge_type", [])

    @rx.var
    def results_domain_items(self) -> list[dict]:
        return self.current_results_data.get("domain", [])

    @rx.var
    def results_rbt_items(self) -> list[dict]:
        return self.current_results_data.get("rbt_level", [])

    @rx.var
    def results_candidate_summary_rows(self) -> list[dict]:
        """Build the candidate summary table exclusively from real AI results.
        Overall Score = sum(normalized_score * weightage / 100) for each evaluated test.
        Falls back to a simple average when weightage totals ≠ 100 (not yet configured).
        Returns an empty list when no evaluations have run."""
        rows: list[dict] = []
        cand_map: dict[str, dict] = {}
        final_test_name = self.selected_assessment_final_test
        asmn = self.selected_assessment_name

        saved_w: dict[str, int] = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        use_weightage = (total_w == 100 and bool(saved_w))

        for key, res in self.real_ai_results_per_candidate.items():
            cand_part = key.split(":")[0]
            test_part = key.split(":")[1].strip() if ":" in key else ""
            cand_name = cand_part.split("(")[0].strip() if "(" in cand_part else cand_part.strip()
            cand_id = cand_part.split("(")[-1].rstrip(")").strip() if "(" in cand_part else ""
            uid = cand_id or cand_name

            norm_score = self._calculate_normalized_score(res)
            score_val = round(norm_score, 1)

            if uid not in cand_map:
                cand_map[uid] = {
                    "name": cand_name,
                    "emp_id": cand_id,
                    "scores": {},
                    "norm_scores": {},
                }
            cand_map[uid]["scores"][test_part] = score_val
            cand_map[uid]["norm_scores"][test_part] = score_val

        target_test = self.selected_test_name.strip()
        for uid, info in cand_map.items():
            scores_map = info["scores"]
            if use_weightage:
                weighted_sum = sum(
                    scores_map.get(t, 0.0) * w / 100.0
                    for t, w in saved_w.items()
                )
                overall = round(weighted_sum, 1)
            else:
                s_vals = list(scores_map.values())
                overall = round(sum(s_vals) / len(s_vals), 1) if s_vals else 0.0

            if target_test and target_test in scores_map:
                t_score = scores_map[target_test]
                t_pass = self.get_test_pass_percentage(target_test)
                result_str = "Passed" if t_score >= t_pass else "Failed"
            else:
                overall_pass = self.get_assessment_overall_pass_percentage()
                result_str = "Passed" if overall >= overall_pass else "Failed"

            final_s = scores_map.get(final_test_name, overall)
            rows.append({
                "rank": len(rows) + 1,
                "name": info["name"],
                "emp_id": info["emp_id"],
                "overall_score": int(round(overall)),
                "overall_score_str": str(overall) if (overall != int(overall)) else str(int(overall)),
                "final_test_score": int(round(final_s)),
                "result": result_str,
            })
        # Re-sort by score descending and re-number ranks
        rows.sort(key=lambda r: r["overall_score"], reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        return rows

    # ── Results Dynamic Computed Vars for Unified Reporting ───────────
    @rx.var(cache=True)
    async def results_assessment_tests(self) -> list[dict]:
        """List of all actual tests created under the selected assessment (Formative 1, 2, ..., Summative)."""
        asmn = self.selected_assessment_name
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        
        tests = []
        seen = set()
        if match:
            for t in match.get("test_items", []):
                t_name = t["name"]
                if t_name not in seen:
                    seen.add(t_name)
                    w = saved_w.get(t_name, t.get("weightage", 0))
                    tests.append({
                        "name": t_name,
                        "is_final": t.get("is_final", False) or "summative" in t_name.lower(),
                        "weightage": int(w) if str(w).isdigit() else 0,
                    })
        return tests

    @rx.var(cache=True)
    async def results_all_tests_headers(self) -> list[str]:
        tests = await self.results_assessment_tests
        return [t["name"] for t in tests]

    @rx.var(cache=True)
    async def results_individual_test_cards(self) -> list[dict]:
        """Dynamically build test cards for the selected candidate."""
        tests = await self.results_assessment_tests
        cand = await self.results_effective_candidate
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        pass_pct = self.results_pass_percentage

        cards = []
        for t in tests:
            t_name = t["name"]
            score_val = None
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                c_part = parts[0].strip()
                t_part = parts[1].strip() if len(parts) > 1 else ""
                pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
                pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
                if t_part == t_name and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower() or cand == c_part):
                    score_val = int(round(self._calculate_normalized_score(val)))
                    break

            w = t["weightage"]
            if score_val is not None:
                is_fail = score_val < pass_pct
                score_str = f"{score_val}%"
            else:
                is_fail = False
                score_str = "Not Evaluated"
            cards.append({
                "name": t_name,
                "score_str": score_str,
                "score_val": score_val if score_val is not None else -1,
                "weightage_str": f"(Weightage: {w}%)",
                "is_fail": is_fail,
            })
        return cards

    @rx.var(cache=True)
    async def results_individual_overall_card(self) -> dict:
        cand = await self.results_effective_candidate
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()

        tests = await self.results_assessment_tests
        saved_w = self.saved_assessment_weightages.get(self.selected_assessment_name, {})
        total_w = sum(saved_w.values())
        use_weightage = (total_w == 100 and bool(saved_w))

        weighted_sum = 0.0
        evaluated_weight_sum = 0.0
        scores = []
        for t in tests:
            t_name = t["name"]
            w = saved_w.get(t_name, t.get("weightage", 0))
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                c_part = parts[0].strip()
                t_part = parts[1].strip() if len(parts) > 1 else ""
                pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
                pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
                if t_part == t_name and ((cand_id and cand_id == pid) or cand_name.lower() == pname.lower() or cand == c_part):
                    s = self._calculate_normalized_score(val)
                    scores.append(s)
                    if use_weightage:
                        weighted_sum += (s * w) / 100.0
                        evaluated_weight_sum += w
                    else:
                        weighted_sum += s
                    break

        pass_pct = self.results_pass_percentage
        if scores:
            if use_weightage and evaluated_weight_sum > 0:
                final_num = int(round(weighted_sum / (evaluated_weight_sum / 100.0)))
            elif scores:
                final_num = int(round(sum(scores) / len(scores)))
            else:
                final_num = 0
            is_passed = final_num >= pass_pct
            return {
                "score_str": f"{final_num}%",
                "score_val": final_num,
                "status_str": "Pass" if is_passed else "Fail",
                "is_passed": is_passed,
                "pass_mark_str": f"Pass Mark: {pass_pct}%",
            }
        else:
            return {
                "score_str": "Not Evaluated",
                "score_val": 0,
                "status_str": "Not Evaluated",
                "is_passed": False,
                "pass_mark_str": f"Pass Mark: {pass_pct}%",
            }

    @rx.var(cache=True)
    async def results_all_test_avg_cards(self) -> list[dict]:
        tests = await self.results_assessment_tests
        cards = []
        for t in tests:
            t_name = t["name"]
            scores = []
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                t_part = parts[1].strip() if len(parts) > 1 else ""
                if t_part == t_name:
                    scores.append(self._calculate_normalized_score(val))
            if scores:
                avg = int(round(sum(scores) / len(scores)))
                score_str = f"{avg}%"
            else:
                avg = -1
                score_str = "Not Evaluated"
            cards.append({
                "name": t_name,
                "score_str": score_str,
                "score_val": avg,
                "subtext": "(Average Score)",
            })
        return cards

    @rx.var(cache=True)
    async def results_all_overall_avg_card(self) -> dict:
        tests = await self.results_assessment_tests
        asmn = self.selected_assessment_name
        saved_w = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        use_weightage = (total_w == 100 and bool(saved_w))

        test_averages = {}
        for t in tests:
            t_name = t["name"]
            scores = []
            for key, val in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                t_part = parts[1].strip() if len(parts) > 1 else ""
                if t_part == t_name:
                    scores.append(self._calculate_normalized_score(val))
            if scores:
                test_averages[t_name] = sum(scores) / len(scores)

        if not test_averages:
            return {
                "score_str": "Not Evaluated",
                "score_val": 0,
                "subtext": "(Average Score)",
            }

        if use_weightage:
            eval_weights = sum(t["weightage"] for t in tests if t["name"] in test_averages)
            if eval_weights > 0:
                overall_avg = int(round(sum(test_averages[t["name"]] * t["weightage"] for t in tests if t["name"] in test_averages) / (eval_weights / 100.0) / 100.0))
            else:
                overall_avg = int(round(sum(test_averages.values()) / len(test_averages)))
        else:
            overall_avg = int(round(sum(test_averages.values()) / len(test_averages)))

        return {
            "score_str": f"{overall_avg}%",
            "score_val": overall_avg,
            "subtext": "(Average Score)",
        }

    @rx.var(cache=True)
    async def results_displayed_questions(self) -> list[dict]:
        cand = await self.results_effective_candidate
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()

        target_test = (self.results_selected_test or "").strip()
        if not target_test or target_test == "All Tests (Overall)":
            tests = await self.results_assessment_tests
            if tests:
                target_test = tests[0]["name"]

        questions = []
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part

            if target_test and t_part != target_test:
                continue

            if (cand_id and cand_id == pid) or (cand_name and cand_name.lower() == pname.lower()) or (cand == c_part):
                for i, q in enumerate(val.get("questions", []), 1):
                    q_num = str(q.get("q_no", i))
                    if not q_num.startswith("Q") and q_num.isdigit():
                        q_display = f"Q{q_num}"
                    else:
                        q_display = q_num
                    try:
                        obt = float(q.get("ai_score", q.get("awarded_marks", 0)) or 0)
                        mx = float(q.get("max_marks", q.get("maximum_marks", 0)) or 0)
                        pct = round((obt / mx) * 100) if mx > 0 else 0
                    except (ValueError, TypeError):
                        obt, mx, pct = 0.0, 0.0, 0
                    obt_str = str(int(obt)) if obt == int(obt) else str(obt)
                    mx_str = str(int(mx)) if mx == int(mx) else str(mx)
                    justification = q.get("justification") or q.get("feedback") or q.get("remarks") or "—"
                    questions.append({
                        "q_no": q_display,
                        "marks_obtained": obt_str,
                        "max_marks": mx_str,
                        "score_pct": f"{pct}%",
                        "justification": justification,
                    })
                if target_test or questions:
                    break

        if not self.show_all_questions and len(questions) > 5:
            return questions[:5]
        return questions

    @rx.var(cache=True)
    async def results_has_more_questions(self) -> bool:
        cand = await self.results_effective_candidate
        cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
        cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()
        target_test = (self.results_selected_test or "").strip()
        if not target_test or target_test == "All Tests (Overall)":
            tests = await self.results_assessment_tests
            if tests:
                target_test = tests[0]["name"]
        total = 0
        for key, val in self.real_ai_results_per_candidate.items():
            parts = key.split(":")
            c_part = parts[0].strip()
            t_part = parts[1].strip() if len(parts) > 1 else ""
            pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if target_test and t_part != target_test:
                continue
            if (cand_id and cand_id == pid) or (cand_name and cand_name.lower() == pname.lower()) or (cand == c_part):
                total = len(val.get("questions", []))
                break
        return total > 5

    @rx.var(cache=True)
    async def results_all_candidates_table_rows(self) -> list[dict]:
        asmn = self.selected_assessment_name
        mine = await self.my_assessments
        match = next((a for a in mine if a["name"] == asmn), None)
        tests = await self.results_assessment_tests
        pass_pct = self.results_pass_percentage

        saved_w = self.saved_assessment_weightages.get(asmn, {})
        total_w = sum(saved_w.values())
        use_weightage = (total_w == 100 and bool(saved_w))

        candidates_list = []
        seen_ids = set()

        if match:
            for c in match.get("candidate_details", []):
                cid = c.get("emp_id", "")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates_list.append({"name": c.get("name", cid), "emp_id": cid})

        for key in self.real_ai_results_per_candidate.keys():
            c_part = key.split(":")[0].strip()
            cid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
            cname = c_part.split("(")[0].strip() if "(" in c_part else c_part
            if cid and cid != "All Candidates" and cid not in seen_ids:
                seen_ids.add(cid)
                candidates_list.append({"name": cname, "emp_id": cid})

        query = (self.results_search_candidate or "").strip().lower()
        rows = []
        for cand in candidates_list:
            cname = cand["name"]
            cid = cand["emp_id"]
            if query and (query not in cname.lower() and query not in cid.lower()):
                continue

            test_scores = []
            weighted_sum = 0.0
            evaluated_count = 0
            evaluated_weight_sum = 0.0

            for t in tests:
                t_name = t["name"]
                t_w = t["weightage"]
                score_val = None
                for key, val in self.real_ai_results_per_candidate.items():
                    parts = key.split(":")
                    c_part = parts[0].strip()
                    t_part = parts[1].strip() if len(parts) > 1 else ""
                    pid = c_part.split("(")[-1].rstrip(")").strip() if "(" in c_part else c_part
                    pname = c_part.split("(")[0].strip() if "(" in c_part else c_part
                    if t_part == t_name and ((cid and cid == pid) or cname.lower() == pname.lower() or f"{cname} ({cid})" == c_part):
                        score_val = int(round(self._calculate_normalized_score(val)))
                        break

                if score_val is not None:
                    evaluated_count += 1
                    is_fail = score_val < pass_pct
                    test_scores.append({
                        "test_name": t_name,
                        "score_str": f"{score_val}%",
                        "is_fail": is_fail,
                    })
                    weighted_sum += (score_val * t_w) / 100.0 if use_weightage else score_val
                    evaluated_weight_sum += t_w
                else:
                    test_scores.append({
                        "test_name": t_name,
                        "score_str": "Not Evaluated",
                        "is_fail": False,
                    })

            if evaluated_count > 0:
                if use_weightage and evaluated_weight_sum > 0:
                    overall_num = int(round(weighted_sum / (evaluated_weight_sum / 100.0)))
                else:
                    overall_num = int(round(weighted_sum / evaluated_count))
                overall_str = f"{overall_num}%"
                is_passed = overall_num >= pass_pct
                status_str = "Pass" if is_passed else "Fail"
            else:
                overall_str = "Not Evaluated"
                is_passed = False
                status_str = "Not Evaluated"

            rows.append({
                "cand_id": cid,
                "cand_name": cname,
                "scores": test_scores,
                "overall_score": overall_str,
                "status": status_str,
                "is_passed": is_passed,
            })

        for i, r in enumerate(rows, 1):
            r["idx"] = str(i)

        return rows

    @rx.var(cache=True)
    async def results_all_candidates_count_str(self) -> str:
        rows = await self.results_all_candidates_table_rows
        return f"Showing 1 to {len(rows)} of {len(rows)} candidates"

    @rx.var(cache=True)
    async def results_summary_stat_cards(self) -> dict:
        test_cards = await self.results_individual_test_cards
        pass_pct = self.results_pass_percentage
        total_tests = len(test_cards)
        passed_tests = sum(1 for t in test_cards if t["score_val"] >= pass_pct)
        overall_card = await self.results_individual_overall_card
        return {
            "total_tests": str(total_tests),
            "passed_tests": str(passed_tests),
            "pass_label": f"Tests ≥ {pass_pct}%",
            "overall_score": overall_card["score_str"],
            "status": overall_card["status_str"],
            "is_passed": overall_card["is_passed"],
        }

    @rx.var(cache=True)
    async def results_bar_chart_items(self) -> list[dict]:
        tab = self.results_active_dimension_tab
        if tab == "test_wise":
            sub_tab = self.results_test_wise_sub_tab
            data = self.current_results_data
            if sub_tab == "co":
                return data.get("co", [])
            elif sub_tab == "lo":
                return data.get("lo", [])
            elif sub_tab == "knowledge_type":
                return data.get("knowledge_type", [])
            elif sub_tab == "domain":
                return data.get("domain", [])
            elif sub_tab == "rbt_level":
                return data.get("rbt_level", [])
            return []
        if tab == "overall":
            if self.results_view_mode == "individual":
                test_cards = await self.results_individual_test_cards
                return [
                    {
                        "name": c["name"],
                        "score": c["score_val"],
                    }
                    for c in test_cards
                    if c.get("score_val", -1) >= 0
                ]
            else:
                avg_cards = await self.results_all_test_avg_cards
                items = []
                for c in avg_cards:
                    val = c.get("score_val", -1)
                    if val >= 0:
                        items.append({"name": c["name"], "score": val})
                return items
        return self.results_current_dimension_items

    @rx.var(cache=True)
    async def results_chart_main_title(self) -> str:
        tab = self.results_active_dimension_tab
        if tab == "test_wise":
            t_name = await self.results_effective_analysis_test
            sub = self.results_test_wise_sub_tab
            sub_title = {
                "co": "Course Outcomes (CO) - Attainment",
                "lo": "Learning Outcomes (LO) - Attainment",
                "knowledge_type": "Knowledge Type Proficiency",
                "domain": "Domain & Topic Competency",
                "rbt_level": "Revised Bloom's Taxonomy (RBT) Level",
                "question_wise": "Question-wise Analysis",
            }.get(sub, "Performance Analysis")
            return f"{sub_title} ({t_name})"
        elif tab == "overall":
            if self.results_view_mode == "individual":
                cname = await self.results_effective_candidate_name
                return f"Overall Performance Across Tests ({cname})"
            else:
                return "Average Performance Across Tests"
        elif tab == "co":
            return "Course Outcomes (CO) - Attainment"
        elif tab == "lo":
            return "Learning Outcomes (LO) - Attainment"
        elif tab == "knowledge_type":
            return "Knowledge Type Proficiency"
        elif tab == "domain":
            return "Domain & Topic Competency"
        elif tab == "rbt_level":
            return "Revised Bloom's Taxonomy (RBT) Level"
        elif tab == "question_wise":
            t_name = await self.results_effective_analysis_test
            return f"Question-wise Analysis ({t_name})"
        return "Performance Analysis"

    @rx.var
    def results_pass_badge_label(self) -> str:
        if self.results_view_mode == "individual":
            return f"Pass Mark: {self.results_pass_percentage}%"
        return f"Target / Pass Mark: {self.results_pass_percentage}%"

    # Format: "Candidate Name (EMP-ID)"
    selected_evaluation_candidate: str = ""
    # Currently selected test in the Evaluation page dropdown
    selected_evaluation_test: str = ""
    show_candidate_response_modal: bool = False
    show_answer_key_upload_modal: bool = False
    show_manual_eval_modal: bool = False
    show_ai_eval_modal: bool = False

    manual_eval_q_index: int = 0
    manual_marks: dict[str, str] = {"0": "4", "1": "3", "2": "5", "3": "4"}
    manual_justifications: dict[str, str] = {
        "0": "Good explanation of workplace safety and its importance.",
        "1": "Listed 2 correct hazards, one minor additional hazard mentioned.",
        "2": "Correctly mentioned standard examples.",
        "3": "Explained most basic hazards clearly.",
    }

    answer_key_uploaded: bool = False
    answer_key_filename: str = ""

    # Per-candidate real AI results (keyed by "Name (EMP-ID)" + ":" + test_name)
    real_ai_results_per_candidate: dict[str, dict] = {}

    def set_selected_evaluation_candidate(self, candidate_name: str):
        self.selected_evaluation_candidate = candidate_name
        # Reset real AI display vars when switching candidates so stale data is cleared
        self.real_ai_score_display = "\u2014"
        self.real_ai_max_score_display = "\u2014"
        self.real_ai_percentage_display = "\u2014"
        self.real_ai_evaluation_date = "Not evaluated"
        self.real_ai_eval_questions = []
        if candidate_name == "All Candidates":
            return
        # Re-load persisted real result if it exists
        key = f"{candidate_name}:{self.selected_test_name}"
        if key in self.real_ai_results_per_candidate:
            saved = self.real_ai_results_per_candidate[key]
            self.real_ai_score_display = saved.get("score", "\u2014")
            self.real_ai_max_score_display = saved.get("max_score", "\u2014")
            self.real_ai_percentage_display = saved.get("percentage", "\u2014")
            self.real_ai_evaluation_date = saved.get("eval_date", "Not evaluated")
            qs = [dict(q) for q in saved.get("questions", [])]
            for q in qs:
                if not q.get("score_pct"):
                    try:
                        q_obt = float(q.get("ai_score", 0) or 0)
                        q_max = float(q.get("max_marks", 0) or 0)
                        q_p = (q_obt / q_max) * 100.0 if q_max > 0 else 0.0
                        q["score_pct"] = f"{int(q_p)}%" if q_p == int(q_p) else f"{round(q_p, 1)}%"
                    except Exception:
                        q["score_pct"] = "0%"
            self.real_ai_eval_questions = qs

    @rx.var
    def is_all_candidates_evaluation(self) -> bool:
        """True when 'All Candidates' is selected in the Evaluation page candidate dropdown."""
        return self.selected_evaluation_candidate == "All Candidates"

    @rx.var
    async def evaluation_candidate_options(self) -> list[str]:
        """Derive candidate options from the real assigned candidates in the current assessment, with 'All Candidates' included."""
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == self.selected_assessment_name:
                options = []
                for c in a.get("candidate_details", []):
                    label = f"{c['name']} ({c['emp_id']})"
                    options.append(label)
                return ["All Candidates"] + options if options else ["All Candidates"]
        return ["All Candidates"]

    @rx.var(cache=True)
    async def evaluation_test_options(self) -> list[str]:
        """Dynamically derive all test names for the current assessment — used by the Evaluation Select Test dropdown."""
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == self.selected_assessment_name:
                return [t["name"] for t in a.get("test_items", [])]
        return []

    def set_evaluation_selected_test(self, test_name: str):
        """Select a test from the Evaluation page dropdown and sync state so all evaluation data updates."""
        self.selected_evaluation_test = test_name
        # Keep the workspace-level selected_test_name in sync so all evaluation queries use this test
        self.selected_test_name = test_name
        # Reset AI result display so stale results from the previous test are cleared
        self.real_ai_score_display = "—"
        self.real_ai_max_score_display = "—"
        self.real_ai_percentage_display = "—"
        self.real_ai_evaluation_date = "Not evaluated"
        self.real_ai_eval_questions = []
        # Re-load persisted AI result for the selected candidate + new test if it exists
        key = f"{self.selected_evaluation_candidate}:{test_name}"
        if key in self.real_ai_results_per_candidate:
            saved = self.real_ai_results_per_candidate[key]
            self.real_ai_score_display = saved.get("score", "—")
            self.real_ai_max_score_display = saved.get("max_score", "—")
            self.real_ai_percentage_display = saved.get("percentage", "—")
            self.real_ai_evaluation_date = saved.get("eval_date", "Not evaluated")
            self.real_ai_eval_questions = [dict(q) for q in saved.get("questions", [])]

    @rx.var
    def current_candidate_eval_data(self) -> dict:
        """Returns real submitted response data if available from candidate_response_service.
        Never falls back to mock/hard-coded candidate answers.
        """
        raw = self.selected_evaluation_candidate
        test_name = self.selected_test_name
        assessment_name = self.selected_assessment_name

        if not raw or raw == "All Candidates":
            return {}

        # Search for real response file matching candidate + assessment + test
        real = _find_candidate_response(raw, test_name, assessment_name)
        if real and real.get("responses"):
            return real

        # Candidate has NOT submitted a response - return empty dict
        return {}

    @rx.var
    def has_submitted_response(self) -> bool:
        """True if the selected candidate has a real submitted response, or True for All Candidates cohort."""
        if self.selected_evaluation_candidate == "All Candidates":
            return True
        return bool(self.current_candidate_eval_data.get("responses"))

    @rx.var
    def has_ai_evaluated_current_candidate(self) -> bool:
        """True if real AI evaluation has been run for the current candidate."""
        return self.real_ai_score_display != "—"

    @rx.var
    def current_candidate_ai_total_score_only(self) -> str:
        disp = self.current_candidate_ai_score_display
        if "/" in disp:
            return disp.split("/")[0].strip()
        return disp if disp != "—" else "0"

    @rx.var
    def current_candidate_ai_max_val(self) -> str:
        disp = self.current_candidate_ai_score_display
        if "/" in disp:
            return disp.split("/")[1].strip()
        return self.real_ai_max_score_display if self.real_ai_max_score_display != "—" else "0"

    @rx.var
    def current_candidate_submitted_on(self) -> str:
        if self.selected_evaluation_candidate == "All Candidates":
            return "All Assigned Candidates"
        return self.current_candidate_eval_data.get("submitted_on", "Not Submitted")

    @rx.var
    def current_candidate_excel_file(self) -> str:
        if self.selected_evaluation_candidate == "All Candidates":
            return "All candidate responses (Batch)"
        return self.current_candidate_eval_data.get("excel_file", "No response file available")

    @rx.var
    def current_candidate_responses(self) -> list[dict]:
        return self.current_candidate_eval_data.get("responses", [])

    @rx.var
    def current_candidate_ai_score_display(self) -> str:
        """Returns real AI score if evaluated, else —."""
        if self.real_ai_score_display != "—":
            return self.real_ai_score_display
        return "—"

    @rx.var
    def current_candidate_ai_percentage_display(self) -> str:
        """Returns real AI percentage if evaluated, else —."""
        if self.real_ai_percentage_display != "—":
            return self.real_ai_percentage_display
        return "—"

    @rx.var
    def current_candidate_ai_eval_questions(self) -> list[dict]:
        """Returns real AI question breakdown if evaluated, else empty list."""
        if self.real_ai_eval_questions:
            return self.real_ai_eval_questions
        return []

    @rx.var
    def current_candidate_ai_eval_date(self) -> str:
        """Returns the real AI evaluation date if available."""
        return self.real_ai_evaluation_date

    @rx.var
    def eval_qp_filename(self) -> str:
        qp = self.question_papers.get(self.selected_assessment_name, {}).get(self.selected_test_name, "")
        return qp if qp else "No question paper available"

    @rx.var
    def has_eval_qp(self) -> bool:
        """True if an actual question paper file is uploaded for the current assessment + test."""
        qp = self.question_papers.get(self.selected_assessment_name, {}).get(self.selected_test_name, "")
        if not qp:
            return False
        p1 = Path(rx.get_upload_dir()) / qp
        p2 = Path("uploaded_files") / qp
        return p1.exists() or p2.exists()

    # Manual Evaluation Navigation & Input computed vars
    @rx.var
    def current_manual_question_obj(self) -> dict:
        resps = self.current_candidate_responses
        if 0 <= self.manual_eval_q_index < len(resps):
            return resps[self.manual_eval_q_index]
        return resps[0] if resps else {}

    @rx.var
    def current_manual_question_text(self) -> str:
        return self.current_manual_question_obj.get("question", "")

    @rx.var
    def current_manual_response_text(self) -> str:
        return self.current_manual_question_obj.get("response", "")

    @rx.var
    def current_manual_mark_val(self) -> str:
        key = str(self.manual_eval_q_index)
        return self.manual_marks.get(key, "4")

    @rx.var
    def current_manual_justification_val(self) -> str:
        key = str(self.manual_eval_q_index)
        return self.manual_justifications.get(key, "")

    def set_current_manual_mark(self, value: str):
        key = str(self.manual_eval_q_index)
        new_marks = dict(self.manual_marks)
        new_marks[key] = value
        self.manual_marks = new_marks

    def set_current_manual_justification(self, value: str):
        key = str(self.manual_eval_q_index)
        new_just = dict(self.manual_justifications)
        new_just[key] = value
        self.manual_justifications = new_just

    def open_candidate_response_modal(self):
        self.show_candidate_response_modal = True

    def set_show_candidate_response_modal(self, value: bool):
        self.show_candidate_response_modal = value

    def open_answer_key_upload(self):
        self.show_answer_key_upload_modal = True

    def set_show_answer_key_upload_modal(self, value: bool):
        self.show_answer_key_upload_modal = value

    def simulate_upload_answer_key(self):
        self.answer_key_uploaded = True
        self.show_answer_key_upload_modal = False
        return rx.toast.success(f"Answer Key '{self.answer_key_filename}' uploaded successfully!")

    async def handle_answer_key_upload(self, files: list[rx.UploadFile]):
        """Upload the answer key Excel file to uploaded_files/ and mark as uploaded."""
        if not files:
            return rx.toast.error("Please select an answer key file to upload.")
        file = files[0]
        upload_data = await file.read()
        try:
            out_dir = Path("uploaded_files")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / file.filename
            with open(out_path, "wb") as f:
                f.write(upload_data)
            self.answer_key_filename = file.filename
            self.answer_key_uploaded_path = str(out_path)
        except Exception:
            pass
        self.answer_key_uploaded = True
        self.show_answer_key_upload_modal = False
        return rx.toast.success(f"Answer Key '{file.filename}' uploaded successfully!")

    def open_manual_eval_modal(self):
        self.manual_eval_q_index = 0
        self.show_manual_eval_modal = True

    def set_show_manual_eval_modal(self, value: bool):
        self.show_manual_eval_modal = value

    def next_manual_question(self):
        if self.manual_eval_q_index < len(self.current_candidate_responses) - 1:
            self.manual_eval_q_index += 1

    def prev_manual_question(self):
        if self.manual_eval_q_index > 0:
            self.manual_eval_q_index -= 1

    def save_manual_evaluation(self):
        resps = self.current_candidate_responses
        if not resps:
            self.show_manual_eval_modal = False
            return rx.toast.info("No candidate responses to evaluate.")

        total_awarded = 0.0
        total_max = 0.0
        breakdown = []
        for i, r in enumerate(resps):
            key = str(i)
            raw_mark = self.manual_marks.get(key, "0")
            raw_just = self.manual_justifications.get(key, "")
            try:
                obt = float(raw_mark)
            except (ValueError, TypeError):
                obt = 0.0
            try:
                mx = float(r.get("marks", r.get("Marks", 0)) or 0)
            except (ValueError, TypeError):
                mx = 10.0 if obt > 0 else 0.0
            if mx <= 0 and obt > 0:
                mx = max(obt, 10.0)

            total_awarded += obt
            total_max += mx

            q_pct = (obt / mx) * 100.0 if mx > 0 else 0.0
            pct_str = f"{int(q_pct)}%" if q_pct == int(q_pct) else f"{round(q_pct, 1)}%"

            q_num = str(r.get("title", r.get("Question No", f"Q{i+1}")))
            q_txt = str(r.get("text", r.get("Question", "")))
            c_ans = str(r.get("response", r.get("Candidate Answer", "")))

            breakdown.append({
                "q_no": q_num,
                "question": q_txt,
                "response": c_ans,
                "ai_score": str(int(obt) if obt == int(obt) else obt),
                "max_marks": str(int(mx) if mx == int(mx) else mx),
                "score_pct": pct_str,
                "justification": raw_just if raw_just else "Manual evaluation",
            })

        norm_pct = round((total_awarded / total_max) * 100.0, 1) if total_max > 0 else 0.0
        norm_str = f"{int(norm_pct)}%" if norm_pct == int(norm_pct) else f"{norm_pct}%"
        disp_awarded = int(total_awarded) if total_awarded == int(total_awarded) else total_awarded
        disp_max = int(total_max) if total_max == int(total_max) else total_max
        disp_score = f"{disp_awarded} / {disp_max}"

        self.real_ai_score_display = disp_score
        self.real_ai_max_score_display = str(disp_max)
        self.real_ai_percentage_display = norm_str
        self.real_ai_evaluation_date = datetime.now().strftime("%d %b %Y, %I:%M %p")
        self.real_ai_eval_questions = breakdown

        k = f"{self.selected_evaluation_candidate}:{self.selected_test_name}"
        saved_results = dict(self.real_ai_results_per_candidate)
        saved_results[k] = {
            "score": disp_score,
            "marks_obtained": total_awarded,
            "max_marks": total_max,
            "normalized_score": norm_pct,
            "max_score": self.real_ai_max_score_display,
            "percentage": norm_str,
            "eval_date": self.real_ai_evaluation_date,
            "questions": breakdown,
        }
        self.real_ai_results_per_candidate = saved_results

        self.show_manual_eval_modal = False
        return rx.toast.success(f"Manual evaluation saved! Score: {disp_score} ({norm_str})")

    def open_ai_eval_modal(self):
        self.show_ai_eval_modal = True

    def set_show_ai_eval_modal(self, value: bool):
        self.show_ai_eval_modal = value

    async def trigger_evaluation_tab_ai_eval(self):
        """Trigger the real AI evaluation from the Evaluation tab modal.
        Closes the modal and delegates to run_ai_evaluation().
        """
        self.show_ai_eval_modal = False
        yield
        async for update in self.run_ai_evaluation():
            yield update

    def download_candidate_response(self):
        return rx.toast.info(f"{self.current_candidate_excel_file} downloaded successfully (Mock Excel)!")

    def download_ai_eval_report(self):
        return rx.toast.info("AI Evaluation Results Report downloaded (Mock PDF/Excel)!")



class FacilitatorProfileState(rx.State):
    """State for the Facilitator Profile page (Mock UI)."""
    emp_id: str = "F001"
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    profile_photo_url: str = ""
    
    designation: str = ""
    department: str = ""
    business_unit: str = ""
    years_experience: str = ""
    
    primary_expertise: str = ""
    specific_skills: str = ""
    
    highest_qualification: str = ""
    specialization: str = ""
    certifications: str = ""
    
    training_experience: str = ""
    assessment_experience: str = ""
    subjects_domains: str = ""
    assessment_types: str = ""
    
    availability: str = ""

    # Setters
    def set_emp_id(self, value: str): self.emp_id = value
    def set_full_name(self, value: str): self.full_name = value
    def set_email(self, value: str): self.email = value
    def set_phone(self, value: str): self.phone = value
    def set_location(self, value: str): self.location = value
    
    def set_designation(self, value: str): self.designation = value
    def set_department(self, value: str): self.department = value
    def set_business_unit(self, value: str): self.business_unit = value
    def set_years_experience(self, value: str): self.years_experience = value
    
    def set_primary_expertise(self, value: str): self.primary_expertise = value
    def set_specific_skills(self, value: str): self.specific_skills = value
    
    def set_highest_qualification(self, value: str): self.highest_qualification = value
    def set_specialization(self, value: str): self.specialization = value
    def set_certifications(self, value: str): self.certifications = value
    
    def set_training_experience(self, value: str): self.training_experience = value
    def set_assessment_experience(self, value: str): self.assessment_experience = value
    def set_subjects_domains(self, value: str): self.subjects_domains = value
    def set_assessment_types(self, value: str): self.assessment_types = value
    
    def set_availability(self, value: str): self.availability = value

    async def load_profile(self):
        """Load profile for the currently authenticated facilitator from shared store."""
        try:
            from ai_hybrid_evaluator.state.auth_state import AuthState
            auth = await self.get_state(AuthState)
            if auth.facilitator_emp_id:
                self.emp_id = auth.facilitator_emp_id
        except Exception:
            pass

        fid = self.emp_id or "F001"
        prof = get_facilitator_profile(
            fid,
            default_name=self.full_name or "Facilitator",
            default_email=self.email,
            default_phone=self.phone,
        )
        self.full_name = prof.get("full_name", "")
        self.email = prof.get("email", "")
        self.phone = prof.get("phone", "")
        self.location = prof.get("location", "")
        self.profile_photo_url = prof.get("profile_photo_url", "")
        self.designation = prof.get("designation", "")
        self.department = prof.get("department", "")
        self.business_unit = prof.get("business_unit", "")
        self.years_experience = prof.get("years_experience", "")
        self.primary_expertise = prof.get("primary_expertise", "")
        self.specific_skills = prof.get("specific_skills", "")
        self.highest_qualification = prof.get("highest_qualification", "")
        self.specialization = prof.get("specialization", "")
        self.certifications = prof.get("certifications", "")
        self.training_experience = prof.get("training_experience", "")
        self.assessment_experience = prof.get("assessment_experience", "")
        self.subjects_domains = prof.get("subjects_domains", "")
        self.assessment_types = prof.get("assessment_types", "")
        self.availability = prof.get("availability", "")

    async def save_profile(self):
        """Save facilitator profile changes to the shared mock store."""
        data = {
            "emp_id": self.emp_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "profile_photo_url": self.profile_photo_url,
            "designation": self.designation,
            "department": self.department,
            "business_unit": self.business_unit,
            "years_experience": self.years_experience,
            "primary_expertise": self.primary_expertise,
            "specific_skills": self.specific_skills,
            "highest_qualification": self.highest_qualification,
            "specialization": self.specialization,
            "certifications": self.certifications,
            "training_experience": self.training_experience,
            "assessment_experience": self.assessment_experience,
            "subjects_domains": self.subjects_domains,
            "assessment_types": self.assessment_types,
            "availability": self.availability,
        }
        save_facilitator_profile(self.emp_id, data)
        return rx.toast.success("Profile saved successfully!")

    async def handle_photo_upload(self, files: list[rx.UploadFile]):
        """Upload and display the selected facilitator profile image immediately."""
        if not files:
            return rx.toast.error("Please select an image file to upload.")

        file = files[0]
        upload_data = await file.read()

        # Determine MIME type
        ext = file.filename.lower().split(".")[-1] if "." in file.filename else "jpeg"
        mime = "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/jpeg"

        # Encode as Base64 Data URL so the photo renders immediately
        b64 = base64.b64encode(upload_data).decode("utf-8")
        self.profile_photo_url = f"data:{mime};base64,{b64}"

        # Write to upload directory for persistence
        try:
            out_dir = rx.get_upload_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_filename = f"facilitator_photo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            with open(out_dir / safe_filename, "wb") as f:
                f.write(upload_data)
        except Exception:
            pass

        # Save photo to shared store
        save_facilitator_profile(self.emp_id, {"profile_photo_url": self.profile_photo_url})
        return rx.toast.success(f"Profile photo updated: {file.filename}")