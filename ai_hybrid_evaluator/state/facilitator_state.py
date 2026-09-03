"""
Facilitator dashboard state.

Identity (who is signed in) lives in AuthState.
The actual data (assessments, candidates) lives in AdminState, since Admin
is the source of truth for it. This state's job is just to filter that
shared data down to "what belongs to the currently signed-in facilitator",
and to enrich it with resolved candidate details.
"""

import reflex as rx
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.models.models import AssessmentDetail

# Valid workspace tab keys
WORKSPACE_TABS = ["question_paper", "evaluation", "results"]


class FacilitatorState(rx.State):
    # ── Dashboard selection ────────────────────────────────────────────
    selected_assessment_index: int = -1
    selected_assessment_name: str = ""

    # ── Workspace tab navigation (state-based, no route change) ───────
    # One of: "question_paper" | "evaluation" | "results"
    active_workspace_tab: str = "question_paper"

    def set_workspace_tab(self, tab: str):
        """Switch the active tab inside the Assessment Workspace."""
        if tab in WORKSPACE_TABS:
            self.active_workspace_tab = tab

    # ── Question Paper uploads (Test-wise) ─────────────────────────────
    # Structure: { assessment_name: { test_name: filename } }
    # E.g. { "Quality": { "Test 1": "Quality_Test1.xlsx", "Final Test": "Final_Eval.xlsx" } }
    question_papers: dict[str, dict[str, str]] = {
        "Quality": {
            "Test 1": "Quality_Technical_Stage1.xlsx",
            "Test 2": "Question sheet.xlsx",
        }
    }

    # Selected test for the workspace (e.g. "Test 1", "Final Test")
    selected_test_name: str = "Test 1"
    is_replacing_qp: bool = False

    def set_selected_test(self, test_name: str):
        """Select a test to view/upload question paper for in the workspace."""
        self.selected_test_name = test_name
        self.is_replacing_qp = False

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
        """Parse the actual uploaded Excel file from disk or populate standard Excel table data."""
        if filename:
            filepath = rx.get_upload_dir() / filename
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
                        self.excel_headers = data[0]
                        self.excel_rows = data[1:]
                        self.excel_sheet_name = f"{sheet.title or 'Questions'}"
                        self.excel_total_rows_count = len(self.excel_rows)
                        self.excel_total_cols_count = len(self.excel_headers)
                        return
                except Exception:
                    pass

        # Fallback to authentic Excel question paper dataset
        is_final = "final" in test_name.lower()
        self.excel_headers = [
            "Q_No", "Question_Text", "Option_A", "Option_B", "Option_C", "Option_D", "Correct_Answer", "Marks", "Domain_Topic"
        ]
        if is_final:
            self.excel_sheet_name = "Final_Evaluation_Questions"
            self.excel_rows = [
                ["1", "Design an end-to-end battery telemetry & health monitoring architecture with fault tolerance.", "N/A (Descriptive)", "N/A", "N/A", "N/A", "Rubric Evaluation", "30", "System Architecture"],
                ["2", "Identify failure modes in thermal management units and define containment response protocols.", "N/A (Case Study)", "N/A", "N/A", "N/A", "Rubric Evaluation", "35", "Quality Assurance & FMEA"],
                ["3", "Implement a real-time anomaly detection routine operating under 50ms latency on edge controllers.", "N/A (Coding Task)", "N/A", "N/A", "N/A", "Test Suite Evaluation", "35", "Software & Algorithms"],
            ]
        else:
            self.excel_sheet_name = "Stage1_Questions"
            self.excel_rows = [
                ["1", "Which international standard specifies quality management systems for automotive production parts?", "ISO 9001", "IATF 16949", "ISO 14001", "ISO 45001", "B", "20", "Quality Standards"],
                ["2", "In statistical quality control, what does a Cpk value > 1.33 indicate?", "Process not capable", "Process capable & centered", "Variation too high", "Limits too tight", "B", "20", "SPC Analysis"],
                ["3", "What is the primary objective of Failure Mode and Effects Analysis (FMEA)?", "Financial audit", "Proactive defect mitigation", "Finished goods audit", "Machine maintenance", "B", "20", "Risk & FMEA"],
                ["4", "Which quality tool is most effective for identifying the vital few causes (80/20 rule)?", "Scatter Plot", "Pareto Chart", "Histogram", "Fishbone Chart", "B", "20", "Quality Tools"],
                ["5", "What initial action should be taken when critical torque threshold fails on the inline station?", "Discard entire batch", "Quarantine suspect units & contain line", "Recalibrate after 100 cycles", "Widen test limits", "B", "20", "Troubleshooting"],
            ]
        self.excel_total_rows_count = len(self.excel_rows)
        self.excel_total_cols_count = len(self.excel_headers)

    def open_qp_preview(self, test_name: str, assessment_name: str = ""):
        """Opens the Question Paper preview dialog for the given test."""
        self.viewing_qp_test_name = test_name
        self.viewing_qp_assessment_name = assessment_name or self.selected_assessment_name
        self.viewing_qp_filename = self.question_papers.get(self.viewing_qp_assessment_name, {}).get(test_name, "")
        self.load_excel_preview_data(self.viewing_qp_filename, test_name)
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

        fac_id = auth_state.facilitator_emp_id
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
            final_test_name = a.get("final_test", "Summative Test")
            all_tests_list = list(regular_tests) + [final_test_name]
            test_dates = a.get("test_dates", {})

            # Build list of TestItem objects with dates
            test_items = []
            for t_name in regular_tests:
                d = test_dates.get(t_name, "")
                test_items.append({
                    "name": t_name,
                    "date": d,
                    "is_final": False,
                })

            final_d = test_dates.get(final_test_name, "")
            test_items.append({
                "name": final_test_name,
                "date": final_d,
                "is_final": True,
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
            tests = assessments[index].get("tests", ["Test 1"])
            self.selected_test_name = tests[0] if tests else "Test 1"
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
                tests = assessments[i].get("tests", ["Test 1"])
                self.selected_test_name = tests[0] if tests else "Test 1"
                break
        self.active_workspace_tab = "question_paper"
        return rx.redirect("/facilitator/assessment")

    # ── AI Evaluation Engine & Candidate Submissions State ───────────────
    is_ai_evaluating: bool = False
    ai_evaluation_done: bool = True
    selected_ai_candidate_id: str = "EMP-101"
    show_ai_detail_modal: bool = False

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

    async def run_ai_evaluation(self):
        """Simulate triggering the AI Evaluation Engine on all candidate submissions."""
        self.is_ai_evaluating = True
        yield
        import asyncio
        await asyncio.sleep(1.2)  # realistic AI evaluation processing simulation
        self.is_ai_evaluating = False
        self.ai_evaluation_done = True
        yield rx.toast.success("AI Hybrid Evaluation completed! Evaluated 4 candidate submissions against Question Paper.")

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

    results_candidate_options: list[str] = [
        "All Candidates",
        "Sneha Kulkarni",
        "Rohan Sharma",
        "Priya Nair",
        "Amit Patel",
    ]

    def set_results_selected_candidate(self, candidate_name: str):
        self.results_selected_candidate = candidate_name

    def set_results_dimension_tab(self, tab_key: str):
        self.results_active_dimension_tab = tab_key

    @rx.var
    def current_results_data(self) -> dict:
        return RESULTS_ANALYTICS_DATA.get(
            self.results_selected_candidate,
            RESULTS_ANALYTICS_DATA["All Candidates"]
        )

    @rx.var
    def results_overall_score_val(self) -> str:
        return str(self.current_results_data.get("overall_score", 78))

    @rx.var
    def results_final_test_score_val(self) -> str:
        return str(self.current_results_data.get("final_test_score", 86))

    @rx.var
    def results_passing_rate_val(self) -> str:
        return str(self.current_results_data.get("passing_rate", "100%"))

    @rx.var
    def results_passing_count_val(self) -> str:
        return str(self.current_results_data.get("passing_count", "4 of 4 Candidates Passed"))

    @rx.var
    def results_insight_diff_val(self) -> int:
        return int(self.current_results_data.get("insight_diff", 14))

    @rx.var
    def results_insight_start_val(self) -> str:
        return str(self.current_results_data.get("insight_start", "Formative 1 (72%)"))

    @rx.var
    def results_insight_end_val(self) -> str:
        return str(self.current_results_data.get("insight_end", "Summative Test (86%)"))

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
        return RESULTS_CANDIDATE_SUMMARY

    # ── Evaluation Tab State ───────────────────────────────────────────
    selected_evaluation_candidate: str = "Priya Sharma (CAND-2031)"
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
    answer_key_filename: str = "Quality_Technical_Stage1_AnswerKey.xlsx"
    
    evaluation_candidate_options: list[str] = [
        "Priya Sharma (CAND-2031)",
        "Arjun Rao (CAND-2054)",
        "Divya Nair (CAND-2061)",
    ]

    def set_selected_evaluation_candidate(self, candidate_name: str):
        self.selected_evaluation_candidate = candidate_name

    @rx.var
    def current_candidate_eval_data(self) -> dict:
        return CANDIDATE_EVALUATION_DATA.get(
            self.selected_evaluation_candidate,
            CANDIDATE_EVALUATION_DATA["Priya Sharma (CAND-2031)"]
        )

    @rx.var
    def current_candidate_submitted_on(self) -> str:
        return self.current_candidate_eval_data.get("submitted_on", "29 Aug 2026, 10:24 AM")

    @rx.var
    def current_candidate_excel_file(self) -> str:
        return self.current_candidate_eval_data.get("excel_file", "Priya_Sharma_Test1_Response.xlsx")

    @rx.var
    def current_candidate_responses(self) -> list[dict]:
        return self.current_candidate_eval_data.get("responses", [])

    @rx.var
    def current_candidate_ai_score_display(self) -> str:
        return self.current_candidate_eval_data.get("ai_score", "38 / 50")

    @rx.var
    def current_candidate_ai_percentage_display(self) -> str:
        return self.current_candidate_eval_data.get("percentage", "76%")

    @rx.var
    def current_candidate_ai_eval_questions(self) -> list[dict]:
        return self.current_candidate_eval_data.get("responses", [])

    @rx.var
    def eval_qp_filename(self) -> str:
        qp = self.question_papers.get(self.selected_assessment_name, {}).get(self.selected_test_name, "")
        return qp if qp else "Quality_Technical_Stage1.xlsx"

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

    def trigger_evaluation_tab_ai_eval(self):
        self.show_ai_eval_modal = False
        return rx.toast.success(f"AI Evaluation completed for {self.selected_evaluation_candidate}! Total Score: 38 / 50 (76%).")

    def download_candidate_response(self):
        return rx.toast.info(f"{self.current_candidate_excel_file} downloaded successfully (Mock Excel)!")

    def download_ai_eval_report(self):
        return rx.toast.info("AI Evaluation Results Report downloaded (Mock PDF/Excel)!")


CANDIDATE_EVALUATION_DATA = {
    "Priya Sharma (CAND-2031)": {
        "emp_id": "CAND-2031",
        "name": "Priya Sharma",
        "submitted_on": "29 Aug 2026, 10:24 AM",
        "excel_file": "Priya_Sharma_Test1_Response.xlsx",
        "ai_score": "38 / 50",
        "percentage": "76%",
        "eval_date": "29 Aug 2026, 11:30 AM",
        "responses": [
            {
                "q_no": "Q1",
                "question": "Why is safety important in the workplace?",
                "response": "Safety is important because it helps in protecting employees from accidents and injuries. It also ensures a healthy work environment and increases productivity.",
                "ai_score": "4",
                "max_marks": "5",
                "justification": "Good explanation of workplace safety and its importance.",
            },
            {
                "q_no": "Q2",
                "question": "Name three common hazards in electrical systems.",
                "response": "Three common hazards are electrical shock, short circuit, and overloading.",
                "ai_score": "3",
                "max_marks": "5",
                "justification": "Listed 2 correct hazards, one minor additional hazard mentioned.",
            },
            {
                "q_no": "Q3",
                "question": "What standards regulate electrical safety?",
                "response": "Some common standards are IEC 60364, NFPA 70E, and ISO 45001.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Correctly mentioned standard examples.",
            },
            {
                "q_no": "Q4",
                "question": "What are basic electrical hazards?",
                "response": "The basic electrical hazards include electric shock, arc flash, fire hazard, and equipment damage.",
                "ai_score": "4",
                "max_marks": "5",
                "justification": "Explained most basic hazards clearly.",
            },
        ],
    },
    "Arjun Rao (CAND-2054)": {
        "emp_id": "CAND-2054",
        "name": "Arjun Rao",
        "submitted_on": "29 Aug 2026, 10:48 AM",
        "excel_file": "Arjun_Rao_Test1_Response.xlsx",
        "ai_score": "42 / 50",
        "percentage": "84%",
        "eval_date": "29 Aug 2026, 11:35 AM",
        "responses": [
            {
                "q_no": "Q1",
                "question": "Why is safety important in the workplace?",
                "response": "Workplace safety prevents industrial downtime, preserves operator wellbeing, and ensures compliance with occupational health regulations.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Comprehensive regulatory and operational safety rationale provided.",
            },
            {
                "q_no": "Q2",
                "question": "Name three common hazards in electrical systems.",
                "response": "Ground fault leakage, insulation degradation, and arc blast flashover.",
                "ai_score": "4",
                "max_marks": "5",
                "justification": "Accurately detailed advanced electrical hazard types.",
            },
            {
                "q_no": "Q3",
                "question": "What standards regulate electrical safety?",
                "response": "Some common standards are IEC 60364, NFPA 70E, and ISO 45001.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Exact standards and industry references identified.",
            },
            {
                "q_no": "Q4",
                "question": "What are basic electrical hazards?",
                "response": "Direct contact shock, electrical burns from arc flash, thermal ignition, and secondary blast injuries.",
                "ai_score": "4",
                "max_marks": "5",
                "justification": "Well-structured categorization of direct and secondary electrical risks.",
            },
        ],
    },
    "Divya Nair (CAND-2061)": {
        "emp_id": "CAND-2061",
        "name": "Divya Nair",
        "submitted_on": "29 Aug 2026, 11:15 AM",
        "excel_file": "Divya_Nair_Test1_Response.xlsx",
        "ai_score": "45 / 50",
        "percentage": "90%",
        "eval_date": "29 Aug 2026, 11:40 AM",
        "responses": [
            {
                "q_no": "Q1",
                "question": "Why is safety important in the workplace?",
                "response": "Safety establishes zero-harm manufacturing culture, mitigates liability, and upholds high assembly line ergonomics and reliability.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Exemplary understanding of zero-harm safety culture.",
            },
            {
                "q_no": "Q2",
                "question": "Name three common hazards in electrical systems.",
                "response": "Short-circuit overcurrent, thermal cable breakdown, and ungrounded chassis voltage.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Flawless identification of critical hazards.",
            },
            {
                "q_no": "Q3",
                "question": "What standards regulate electrical safety?",
                "response": "Some common standards are IEC 60364, NFPA 70E, and ISO 45001.",
                "ai_score": "5",
                "max_marks": "5",
                "justification": "Precise identification of global electrical safety codes.",
            },
            {
                "q_no": "Q4",
                "question": "What are basic electrical hazards?",
                "response": "Shock voltage gradients, arc flash plasma bursts, cable insulation breakdown, and electrical fire propagation.",
                "ai_score": "4",
                "max_marks": "5",
                "justification": "Detailed and accurate technical descriptions.",
            },
        ],
    },
}

RESULTS_ANALYTICS_DATA = {
    "All Candidates": {
        "overall_score": 78,
        "final_test_score": 86,
        "passing_rate": "100%",
        "passing_count": "4 of 4 Candidates Passed",
        "tests": [
            {"name": "Formative 1", "score": 72, "is_final": False},
            {"name": "Formative 2", "score": 68, "is_final": False},
            {"name": "Formative 3", "score": 81, "is_final": False},
            {"name": "Summative Test", "score": 86, "is_final": True},
        ],
        "co": [
            {"name": "CO1 - Engineering Fundamentals & Standards", "code": "CO1", "score": 82},
            {"name": "CO2 - Statistical Process Control (SPC)", "code": "CO2", "score": 76},
            {"name": "CO3 - Defect Prevention & FMEA Mitigation", "code": "CO3", "score": 91},
            {"name": "CO4 - Production Line Containment Protocols", "code": "CO4", "score": 68},
        ],
        "lo": [
            {"name": "LO1 - Identify IATF 16949 Standards", "code": "LO1", "score": 88},
            {"name": "LO2 - Calculate Process Capability Cpk", "code": "LO2", "score": 74},
            {"name": "LO3 - Prioritize Root Causes with Pareto", "code": "LO3", "score": 82},
            {"name": "LO4 - Execute Immediate Containment SOP", "code": "LO4", "score": 79},
            {"name": "LO5 - Formulate Corrective Action Plans", "code": "LO5", "score": 90},
        ],
        "knowledge_type": [
            {"name": "Conceptual Knowledge", "code": "Conceptual", "score": 84},
            {"name": "Procedural Knowledge", "code": "Procedural", "score": 78},
            {"name": "Application Knowledge", "code": "Application", "score": 72},
        ],
        "domain": [
            {"name": "EV Safety & High Voltage Standards", "code": "EV Safety", "score": 86},
            {"name": "Battery Systems & Telemetry Monitoring", "code": "Battery Systems", "score": 79},
            {"name": "Charging Architecture & Thermal Control", "code": "Charging", "score": 74},
            {"name": "Quality Control & Inline Troubleshooting", "code": "Quality Control", "score": 88},
        ],
        "rbt_level": [
            {"name": "Remember (Recall Facts & Definitions)", "code": "Remember", "score": 91},
            {"name": "Understand (Explain Concepts & Principles)", "code": "Understand", "score": 84},
            {"name": "Apply (Execute Operational Procedures)", "code": "Apply", "score": 76},
            {"name": "Analyze (Diagnose Faults & Root Causes)", "code": "Analyze", "score": 68},
        ],
        "insight_diff": 14,
        "insight_start": "Formative 1 (72%)",
        "insight_end": "Summative Test (86%)",
    },
    "Sneha Kulkarni": {
        "emp_id": "EMP-104",
        "overall_score": 96,
        "final_test_score": 94,
        "passing_rate": "100%",
        "passing_count": "All Tests Cleared",
        "tests": [
            {"name": "Formative 1", "score": 90, "is_final": False},
            {"name": "Formative 2", "score": 92, "is_final": False},
            {"name": "Formative 3", "score": 94, "is_final": False},
            {"name": "Summative Test", "score": 96, "is_final": True},
        ],
        "co": [
            {"name": "CO1 - Engineering Fundamentals & Standards", "code": "CO1", "score": 98},
            {"name": "CO2 - Statistical Process Control (SPC)", "code": "CO2", "score": 94},
            {"name": "CO3 - Defect Prevention & FMEA Mitigation", "code": "CO3", "score": 96},
            {"name": "CO4 - Production Line Containment Protocols", "code": "CO4", "score": 92},
        ],
        "lo": [
            {"name": "LO1 - Identify IATF 16949 Standards", "code": "LO1", "score": 100},
            {"name": "LO2 - Calculate Process Capability Cpk", "code": "LO2", "score": 95},
            {"name": "LO3 - Prioritize Root Causes with Pareto", "code": "LO3", "score": 92},
            {"name": "LO4 - Execute Immediate Containment SOP", "code": "LO4", "score": 94},
            {"name": "LO5 - Formulate Corrective Action Plans", "code": "LO5", "score": 98},
        ],
        "knowledge_type": [
            {"name": "Conceptual Knowledge", "code": "Conceptual", "score": 96},
            {"name": "Procedural Knowledge", "code": "Procedural", "score": 94},
            {"name": "Application Knowledge", "code": "Application", "score": 92},
        ],
        "domain": [
            {"name": "EV Safety & High Voltage Standards", "code": "EV Safety", "score": 98},
            {"name": "Battery Systems & Telemetry Monitoring", "code": "Battery Systems", "score": 94},
            {"name": "Charging Architecture & Thermal Control", "code": "Charging", "score": 92},
            {"name": "Quality Control & Inline Troubleshooting", "code": "Quality Control", "score": 96},
        ],
        "rbt_level": [
            {"name": "Remember (Recall Facts & Definitions)", "code": "Remember", "score": 98},
            {"name": "Understand (Explain Concepts & Principles)", "code": "Understand", "score": 96},
            {"name": "Apply (Execute Operational Procedures)", "code": "Apply", "score": 94},
            {"name": "Analyze (Diagnose Faults & Root Causes)", "code": "Analyze", "score": 90},
        ],
        "insight_diff": 6,
        "insight_start": "Formative 1 (90%)",
        "insight_end": "Summative Test (96%)",
    },
    "Rohan Sharma": {
        "emp_id": "EMP-101",
        "overall_score": 92,
        "final_test_score": 90,
        "passing_rate": "100%",
        "passing_count": "All Tests Cleared",
        "tests": [
            {"name": "Formative 1", "score": 74, "is_final": False},
            {"name": "Formative 2", "score": 70, "is_final": False},
            {"name": "Formative 3", "score": 84, "is_final": False},
            {"name": "Summative Test", "score": 92, "is_final": True},
        ],
        "co": [
            {"name": "CO1 - Engineering Fundamentals & Standards", "code": "CO1", "score": 94},
            {"name": "CO2 - Statistical Process Control (SPC)", "code": "CO2", "score": 88},
            {"name": "CO3 - Defect Prevention & FMEA Mitigation", "code": "CO3", "score": 92},
            {"name": "CO4 - Production Line Containment Protocols", "code": "CO4", "score": 85},
        ],
        "lo": [
            {"name": "LO1 - Identify IATF 16949 Standards", "code": "LO1", "score": 95},
            {"name": "LO2 - Calculate Process Capability Cpk", "code": "LO2", "score": 86},
            {"name": "LO3 - Prioritize Root Causes with Pareto", "code": "LO3", "score": 88},
            {"name": "LO4 - Execute Immediate Containment SOP", "code": "LO4", "score": 90},
            {"name": "LO5 - Formulate Corrective Action Plans", "code": "LO5", "score": 92},
        ],
        "knowledge_type": [
            {"name": "Conceptual Knowledge", "code": "Conceptual", "score": 92},
            {"name": "Procedural Knowledge", "code": "Procedural", "score": 86},
            {"name": "Application Knowledge", "code": "Application", "score": 84},
        ],
        "domain": [
            {"name": "EV Safety & High Voltage Standards", "code": "EV Safety", "score": 92},
            {"name": "Battery Systems & Telemetry Monitoring", "code": "Battery Systems", "score": 88},
            {"name": "Charging Architecture & Thermal Control", "code": "Charging", "score": 82},
            {"name": "Quality Control & Inline Troubleshooting", "code": "Quality Control", "score": 90},
        ],
        "rbt_level": [
            {"name": "Remember (Recall Facts & Definitions)", "code": "Remember", "score": 96},
            {"name": "Understand (Explain Concepts & Principles)", "code": "Understand", "score": 90},
            {"name": "Apply (Execute Operational Procedures)", "code": "Apply", "score": 84},
            {"name": "Analyze (Diagnose Faults & Root Causes)", "code": "Analyze", "score": 78},
        ],
        "insight_diff": 18,
        "insight_start": "Formative 1 (74%)",
        "insight_end": "Summative Test (92%)",
    },
    "Priya Nair": {
        "emp_id": "EMP-102",
        "overall_score": 86,
        "final_test_score": 84,
        "passing_rate": "100%",
        "passing_count": "All Tests Cleared",
        "tests": [
            {"name": "Formative 1", "score": 80, "is_final": False},
            {"name": "Formative 2", "score": 76, "is_final": False},
            {"name": "Formative 3", "score": 82, "is_final": False},
            {"name": "Summative Test", "score": 86, "is_final": True},
        ],
        "co": [
            {"name": "CO1 - Engineering Fundamentals & Standards", "code": "CO1", "score": 88},
            {"name": "CO2 - Statistical Process Control (SPC)", "code": "CO2", "score": 82},
            {"name": "CO3 - Defect Prevention & FMEA Mitigation", "code": "CO3", "score": 86},
            {"name": "CO4 - Production Line Containment Protocols", "code": "CO4", "score": 78},
        ],
        "lo": [
            {"name": "LO1 - Identify IATF 16949 Standards", "code": "LO1", "score": 90},
            {"name": "LO2 - Calculate Process Capability Cpk", "code": "LO2", "score": 80},
            {"name": "LO3 - Prioritize Root Causes with Pareto", "code": "LO3", "score": 84},
            {"name": "LO4 - Execute Immediate Containment SOP", "code": "LO4", "score": 82},
            {"name": "LO5 - Formulate Corrective Action Plans", "code": "LO5", "score": 88},
        ],
        "knowledge_type": [
            {"name": "Conceptual Knowledge", "code": "Conceptual", "score": 88},
            {"name": "Procedural Knowledge", "code": "Procedural", "score": 82},
            {"name": "Application Knowledge", "code": "Application", "score": 76},
        ],
        "domain": [
            {"name": "EV Safety & High Voltage Standards", "code": "EV Safety", "score": 88},
            {"name": "Battery Systems & Telemetry Monitoring", "code": "Battery Systems", "score": 82},
            {"name": "Charging Architecture & Thermal Control", "code": "Charging", "score": 78},
            {"name": "Quality Control & Inline Troubleshooting", "code": "Quality Control", "score": 86},
        ],
        "rbt_level": [
            {"name": "Remember (Recall Facts & Definitions)", "code": "Remember", "score": 92},
            {"name": "Understand (Explain Concepts & Principles)", "code": "Understand", "score": 86},
            {"name": "Apply (Execute Operational Procedures)", "code": "Apply", "score": 78},
            {"name": "Analyze (Diagnose Faults & Root Causes)", "code": "Analyze", "score": 72},
        ],
        "insight_diff": 6,
        "insight_start": "Formative 1 (80%)",
        "insight_end": "Summative Test (86%)",
    },
    "Amit Patel": {
        "emp_id": "EMP-103",
        "overall_score": 78,
        "final_test_score": 76,
        "passing_rate": "100%",
        "passing_count": "All Tests Cleared",
        "tests": [
            {"name": "Formative 1", "score": 68, "is_final": False},
            {"name": "Formative 2", "score": 64, "is_final": False},
            {"name": "Formative 3", "score": 74, "is_final": False},
            {"name": "Summative Test", "score": 78, "is_final": True},
        ],
        "co": [
            {"name": "CO1 - Engineering Fundamentals & Standards", "code": "CO1", "score": 80},
            {"name": "CO2 - Statistical Process Control (SPC)", "code": "CO2", "score": 70},
            {"name": "CO3 - Defect Prevention & FMEA Mitigation", "code": "CO3", "score": 82},
            {"name": "CO4 - Production Line Containment Protocols", "code": "CO4", "score": 64},
        ],
        "lo": [
            {"name": "LO1 - Identify IATF 16949 Standards", "code": "LO1", "score": 82},
            {"name": "LO2 - Calculate Process Capability Cpk", "code": "LO2", "score": 68},
            {"name": "LO3 - Prioritize Root Causes with Pareto", "code": "LO3", "score": 76},
            {"name": "LO4 - Execute Immediate Containment SOP", "code": "LO4", "score": 70},
            {"name": "LO5 - Formulate Corrective Action Plans", "code": "LO5", "score": 80},
        ],
        "knowledge_type": [
            {"name": "Conceptual Knowledge", "code": "Conceptual", "score": 80},
            {"name": "Procedural Knowledge", "code": "Procedural", "score": 72},
            {"name": "Application Knowledge", "code": "Application", "score": 68},
        ],
        "domain": [
            {"name": "EV Safety & High Voltage Standards", "code": "EV Safety", "score": 80},
            {"name": "Battery Systems & Telemetry Monitoring", "code": "Battery Systems", "score": 74},
            {"name": "Charging Architecture & Thermal Control", "code": "Charging", "score": 68},
            {"name": "Quality Control & Inline Troubleshooting", "code": "Quality Control", "score": 78},
        ],
        "rbt_level": [
            {"name": "Remember (Recall Facts & Definitions)", "code": "Remember", "score": 86},
            {"name": "Understand (Explain Concepts & Principles)", "code": "Understand", "score": 78},
            {"name": "Apply (Execute Operational Procedures)", "code": "Apply", "score": 70},
            {"name": "Analyze (Diagnose Faults & Root Causes)", "code": "Analyze", "score": 62},
        ],
        "insight_diff": 10,
        "insight_start": "Formative 1 (68%)",
        "insight_end": "Summative Test (78%)",
    },
}

RESULTS_CANDIDATE_SUMMARY = [
    {
        "rank": 1,
        "name": "Sneha Kulkarni",
        "emp_id": "EMP-104",
        "overall_score": 96,
        "final_test_score": 94,
        "result": "Passed",
    },
    {
        "rank": 2,
        "name": "Rohan Sharma",
        "emp_id": "EMP-101",
        "overall_score": 92,
        "final_test_score": 90,
        "result": "Passed",
    },
    {
        "rank": 3,
        "name": "Priya Nair",
        "emp_id": "EMP-102",
        "overall_score": 86,
        "final_test_score": 84,
        "result": "Passed",
    },
    {
        "rank": 4,
        "name": "Amit Patel",
        "emp_id": "EMP-103",
        "overall_score": 78,
        "final_test_score": 76,
        "result": "Passed",
    },
]

class FacilitatorProfileState(rx.State):
    """State for the Facilitator Profile page (Mock UI)."""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    profile_photo_url: str = "/placeholder_avatar.png"
    
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

    async def save_profile(self):
        """Mock save action."""
        return rx.toast.success("Profile saved successfully!")

    async def simulate_upload_photo(self):
        """Mock upload photo action."""
        return rx.toast.info("Photo uploaded! (Mock frontend action)")