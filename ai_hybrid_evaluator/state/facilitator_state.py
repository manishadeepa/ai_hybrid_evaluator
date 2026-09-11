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
WORKSPACE_TABS = ["question_paper", "evaluation", "results"]


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
    # One of: "question_paper" | "evaluation" | "results"
    active_workspace_tab: str = "question_paper"

    def set_workspace_tab(self, tab: str):
        """Switch the active tab inside the Assessment Workspace."""
        if tab in WORKSPACE_TABS:
            self.active_workspace_tab = tab

    # ── Question Paper uploads (Test-wise) ─────────────────────────────
    # Structure: { assessment_name: { test_name: filename } }
    question_papers: dict[str, dict[str, str]] = {}

    # Selected test for the workspace (e.g. "Formative 1", "Summative Test")
    selected_test_name: str = ""
    is_replacing_qp: bool = False

    def set_selected_test(self, test_name: str):
        """Select a test to view/upload question paper for in the workspace."""
        self.selected_test_name = test_name
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

            # Build list of TestItem objects with dates and has_qp
            test_items = []
            for t_name in regular_tests:
                d = test_dates.get(t_name, "")
                has_qp = bool(qp_dict.get(t_name, "") or admin_qp_dict.get(t_name, ""))
                test_items.append({
                    "name": t_name,
                    "date": d,
                    "is_final": False,
                    "has_qp": has_qp,
                })

            if final_test_name:
                final_d = test_dates.get(final_test_name, "")
                has_qp = bool(qp_dict.get(final_test_name, "") or admin_qp_dict.get(final_test_name, ""))
                test_items.append({
                    "name": final_test_name,
                    "date": final_d,
                    "is_final": True,
                    "has_qp": has_qp,
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
            all_t = list(tests) + ([final_test] if final_test else [])
            self.selected_test_name = all_t[0] if all_t else ""
            # Cache candidate details for sync vars (e.g. results_candidate_options)
            self._current_assessment_candidates = [
                {"name": c["name"], "emp_id": c["emp_id"]}
                for c in admin_state.candidates
                if c["emp_id"] in assessments[index].get("assigned_candidates", [])
            ]
        # Always land on the Question Paper tab when opening a workspace
        self.active_workspace_tab = "question_paper"
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
                # Cache candidate details for sync vars
                self._current_assessment_candidates = [
                    {"name": c["name"], "emp_id": c["emp_id"]}
                    for c in admin_state.candidates
                    if c["emp_id"] in a.get("assigned_candidates", [])
                ]
                break
        self.active_workspace_tab = "question_paper"
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
                break
        self.active_workspace_tab = "question_paper"
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
        return rx.toast.info(f"Test '{test_name}' removed from {name}.")

    # ── AI Evaluation Engine & Candidate Submissions State ───────────────
    is_ai_evaluating: bool = False

    ai_evaluation_done: bool = True
    selected_ai_candidate_id: str = "EMP-101"
    show_ai_detail_modal: bool = False

    # ── AI Evaluation Progress Modal State ──────────────────────────────
    show_eval_progress_modal: bool = False
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

    async def run_ai_evaluation(self):
        """Run the real AI Evaluation Engine using Azure OpenAI.
        Reads the uploaded Question Paper and the latest candidate response file.
        Falls back gracefully to mock data if files or API credentials are missing.
        """
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
                    if future.done():
                        break
                    await asyncio.sleep(step)
                    elapsed += step

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

            # Close progress modal as soon as all questions are visually complete
            self.show_eval_progress_modal = False
            yield

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
                self.real_ai_score_display = f"{int(total_awarded)} / {int(total_max)}"
                self.real_ai_max_score_display = str(int(total_max))
                self.real_ai_percentage_display = f"{pct}%"
            elif results_list:
                total_awarded = sum(float(r.get("awarded_marks", 0)) for r in results_list)
                total_max = sum(float(r.get("maximum_marks", r.get("max_marks", 0))) for r in results_list)
                pct = round((total_awarded / total_max) * 100, 1) if total_max > 0 else 0
                self.real_ai_score_display = f"{int(total_awarded)} / {int(total_max)}"
                self.real_ai_max_score_display = str(int(total_max))
                self.real_ai_percentage_display = f"{pct}%"

            self.real_ai_evaluation_date = datetime.now().strftime("%d %b %Y, %I:%M %p")

            # Build question-wise breakdown for UI
            breakdown = []
            for r in results_list:
                breakdown.append({
                    "q_no": str(r.get("question_no", "")),
                    "question": str(r.get("question", "")),
                    "response": str(r.get("candidate_answer", "")),
                    "ai_score": str(r.get("awarded_marks", "")),
                    "max_marks": str(r.get("maximum_marks", r.get("max_marks", ""))),
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
            saved_results[key] = {
                "score": self.real_ai_score_display,
                "max_score": self.real_ai_max_score_display,
                "percentage": self.real_ai_percentage_display,
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
    results_active_dimension_tab: str = "overall"  # "overall", "co", "lo", "knowledge_type", "domain", "rbt_level"
    # Sync cache of the current assessment's candidates — populated in open_assessment handlers
    _current_assessment_candidates: list[dict] = []

    def set_results_selected_candidate(self, candidate_name: str):
        self.results_selected_candidate = candidate_name

    def set_results_dimension_tab(self, tab_key: str):
        self.results_active_dimension_tab = tab_key

    @rx.var(cache=True)
    async def results_candidate_options(self) -> list[str]:
        """Derive Results candidate dropdown dynamically from the actual candidates assigned to the currently selected assessment."""
        options = ["All Candidates"]
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
            if cand_part and cand_part not in options:
                options.append(cand_part)

        return options

    @rx.var
    def current_results_data(self) -> dict:
        """Build results data exclusively from real AI evaluation results.
        Returns an empty dict if no real data exists for the selection."""
        cand = self.results_selected_candidate

        if cand == "All Candidates":
            # Aggregate across all real results for this assessment + selected test
            all_scores = []
            test_scores: dict[str, list] = {}
            co_agg: dict[str, list] = {}
            lo_agg: dict[str, list] = {}
            rbt_agg: dict[str, list] = {}
            domain_agg: dict[str, list] = {}
            kt_agg: dict[str, list] = {}

            target_test = self.selected_test_name.strip()
            for key, res in self.real_ai_results_per_candidate.items():
                parts = key.split(":")
                test_name = parts[1].strip() if len(parts) > 1 else ""
                # Filter by selected test if test is selected
                if target_test and test_name and target_test != test_name:
                    continue
                pct_str = res.get("percentage", "0%").replace("%", "").strip()
                try:
                    score_val = int(float(pct_str))
                except Exception:
                    score_val = 0
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
            avg = int(sum(all_scores) / len(all_scores))
            passed = sum(1 for s in all_scores if s >= 50)
            tests_bar = [
                {"name": t, "score": int(sum(v) / len(v)), "is_final": False}
                for t, v in test_scores.items()
            ]
            co_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in co_agg.items()]
            lo_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in lo_agg.items()]
            rbt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in rbt_agg.items()]
            domain_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in domain_agg.items()]
            kt_items = [{"name": k, "code": k, "score": int(sum(v) / len(v))} for k, v in kt_agg.items()]

            return {
                "overall_score": avg,
                "final_test_score": avg,
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
            }
        else:
            # Per-candidate: find actual evaluation result for this candidate + selected assessment + test
            target_test = self.selected_test_name.strip()
            cand_id = cand.split("(")[-1].rstrip(")").strip() if "(" in cand else cand.strip()
            cand_name = cand.split("(")[0].strip() if "(" in cand else cand.strip()

            matched: dict = {}
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
                    matched = res
                    break

            if not matched:
                return {}  # Candidate has no evaluation result for this test -> show No Results Available
            pct_str = matched.get("percentage", "0%").replace("%", "").strip()
            try:
                score_val = int(float(pct_str))
            except Exception:
                score_val = 0
            test_name = self.selected_test_name or "Test"
            return {
                "overall_score": score_val,
                "final_test_score": score_val,
                "passing_rate": "100%" if score_val >= 50 else "0%",
                "passing_count": "Passed" if score_val >= 50 else "Failed",
                "tests": [{"name": test_name, "score": score_val, "is_final": True}],
                "co": matched.get("co", []),
                "lo": matched.get("lo", []),
                "knowledge_type": matched.get("knowledge_type", []),
                "domain": matched.get("domain", []),
                "rbt_level": matched.get("rbt_level", []),
                "insight_diff": 0,
                "insight_start": "",
                "insight_end": test_name + f" ({score_val}%)",
            }

    @rx.var
    def results_is_passing(self) -> bool:
        return self.current_results_data.get("overall_score", 0) >= 50

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
            return f"OVERALL PERFORMANCE ({cand})"
        elif tab == "co":
            return f"COURSE OUTCOMES - CO ATTAINMENT ({cand})"
        elif tab == "lo":
            return f"LEARNING OUTCOMES - LO ATTAINMENT ({cand})"
        elif tab == "knowledge_type":
            return f"KNOWLEDGE TYPE PROFICIENCY ({cand})"
        elif tab == "domain":
            return f"DOMAIN & TOPIC COMPETENCY ({cand})"
        elif tab == "rbt_level":
            return f"REVISED BLOOM'S TAXONOMY - RBT LEVEL ({cand})"
        return f"PERFORMANCE ANALYSIS ({cand})"

    @rx.var
    def results_tests_items(self) -> list[dict]:
        return self.current_results_data.get("tests", [])

    @rx.var
    def results_current_dimension_items(self) -> list[dict]:
        tab = self.results_active_dimension_tab
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
        return data.get("tests", [])

    @rx.var
    def results_candidate_summary_rows(self) -> list[dict]:
        """Build the candidate summary table exclusively from real AI results.
        Falls back to an empty list (no mock data) when no evaluations have run."""
        rows: list[dict] = []
        seen: set[str] = set()
        for key, res in self.real_ai_results_per_candidate.items():
            cand_part = key.split(":")[0]
            cand_name = cand_part.split("(")[0].strip() if "(" in cand_part else cand_part.strip()
            cand_id = cand_part.split("(")[-1].rstrip(")").strip() if "(" in cand_part else ""
            pct_str = res.get("percentage", "0%").replace("%", "").strip()
            try:
                score_val = int(float(pct_str))
            except Exception:
                score_val = 0
            uid = cand_id or cand_name
            if uid in seen:
                # Update existing row if this result is better/newer
                for r in rows:
                    if r.get("emp_id") == cand_id or r.get("name") == cand_name:
                        r["overall_score"] = score_val
                        r["final_test_score"] = score_val
                        r["result"] = "Passed" if score_val >= 50 else "Failed"
                continue
            seen.add(uid)
            rows.append({
                "rank": len(rows) + 1,
                "name": cand_name,
                "emp_id": cand_id,
                "overall_score": score_val,
                "final_test_score": score_val,
                "result": "Passed" if score_val >= 50 else "Failed",
            })
        # Re-sort by score descending and re-number ranks
        rows.sort(key=lambda r: r["overall_score"], reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        return rows

    # ── Evaluation Tab State ───────────────────────────────────────────
    # Format: "Candidate Name (EMP-ID)"
    selected_evaluation_candidate: str = ""
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
        # Re-load persisted real result if it exists
        key = f"{candidate_name}:{self.selected_test_name}"
        if key in self.real_ai_results_per_candidate:
            saved = self.real_ai_results_per_candidate[key]
            self.real_ai_score_display = saved.get("score", "\u2014")
            self.real_ai_max_score_display = saved.get("max_score", "\u2014")
            self.real_ai_percentage_display = saved.get("percentage", "\u2014")
            self.real_ai_evaluation_date = saved.get("eval_date", "Not evaluated")
            self.real_ai_eval_questions = saved.get("questions", [])

    @rx.var(cache=True)
    async def evaluation_candidate_options(self) -> list[str]:
        """Derive candidate options from the real assigned candidates in the current assessment."""
        mine = await self.my_assessments
        for a in mine:
            if a["name"] == self.selected_assessment_name:
                options = []
                for c in a.get("candidate_details", []):
                    label = f"{c['name']} ({c['emp_id']})"
                    options.append(label)
                return options if options else ["No candidates assigned"]
        return ["No candidates assigned"]

    @rx.var
    def current_candidate_eval_data(self) -> dict:
        """Returns real submitted response data if available from candidate_response_service.
        Never falls back to mock/hard-coded candidate answers.
        """
        raw = self.selected_evaluation_candidate
        test_name = self.selected_test_name
        assessment_name = self.selected_assessment_name

        if not raw:
            return {}

        # Search for real response file matching candidate + assessment + test
        real = _find_candidate_response(raw, test_name, assessment_name)
        if real and real.get("responses"):
            return real

        # Candidate has NOT submitted a response - return empty dict
        return {}

    @rx.var
    def has_submitted_response(self) -> bool:
        """True if the selected candidate has a real submitted response."""
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
        return self.current_candidate_eval_data.get("submitted_on", "Not Submitted")

    @rx.var
    def current_candidate_excel_file(self) -> str:
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
        self.show_manual_eval_modal = False
        return rx.toast.success(f"Manual evaluation for {self.selected_evaluation_candidate} saved successfully!")

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