"""
Candidate State â€” manages candidate dashboard and active test environment session.
Includes question loading from Facilitator-uploaded papers, answers, navigation,
proctoring alerts, and submission flow.
"""

import asyncio
import base64
import re
from datetime import datetime
from pathlib import Path
import reflex as rx
import pandas as pd
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.models.models import get_candidate_profile, save_candidate_profile
from ai_hybrid_evaluator.services.candidate_response_service import save_candidate_response


# â”€â”€ Per-session question store â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Key: "{assessment_name}::{test_name}"
# Value: list of question dicts loaded from the Facilitator-uploaded file.
# Populated in start_test / on_test_page_load from FacilitatorState.question_papers.
LOADED_TEST_QUESTIONS: dict[str, list[dict]] = {}


def _load_questions_from_file(filepath: Path) -> list[dict]:
    """Parse an uploaded question-paper Excel file and return a list of question dicts.
    Detects Objective questions by the presence of Option_A / Option A columns.
    Detects Subjective questions otherwise.
    Preserves the row order of the uploaded file exactly."""
    if not filepath.exists():
        print(f"[QP] File not found: {filepath}")
        return []
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"[QP] Failed to read {filepath}: {e}")
        return []

    cols = [str(c).strip() for c in df.columns]
    # Detect format by looking for option columns
    has_option_cols = any(c in cols for c in [
        "Option_A", "Option A", "Option_B", "Option B",
        "Option_C", "Option C", "Option_D", "Option D",
    ])
    # Also detect inline A) / B) format (single Question column with embedded options)
    has_inline_options = (
        not has_option_cols
        and "Question" in cols
        and df["Question"].astype(str).str.contains(r"\n[A-D]\)", regex=True).any()
    )

    questions: list[dict] = []

    def _safe(row, *keys, default=""):
        for k in keys:
            v = row.get(k)
            if v is not None and pd.notna(v) and str(v).strip():
                return str(v).strip()
        return default

    for _, row in df.iterrows():
        idx = len(questions) + 1

        if has_option_cols:
            # â”€â”€ Structured Objective (separate option columns) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            questions.append({
                "id": idx,
                "title": f"Q{idx}",
                "marks": int(float(_safe(row, "Marks", default="1"))),
                "co": _safe(row, "CO", default=""),
                "lo": _safe(row, "LO", default=""),
                "knowledge_type": _safe(row, "Knowledge Type", default=""),
                "category": _safe(row, "Topic_Domain", "Domain", "Category", default=""),
                "rbt_level": _safe(row, "RBT level", "RBT_Level", default=""),
                "text": _safe(row, "Question_Text", "Question", default=""),
                "question_type": "Objective",
                "options": {
                    "A": _safe(row, "Option_A", "Option A", default=""),
                    "B": _safe(row, "Option_B", "Option B", default=""),
                    "C": _safe(row, "Option_C", "Option C", default=""),
                    "D": _safe(row, "Option_D", "Option D", default=""),
                },
                "correct_option": _safe(row, "Correct_Option", "Answer Key", default=""),
                "guidelines": [],
            })

        elif has_inline_options:
            # â”€â”€ Inline Objective (A) B) C) D) embedded in Question text) â”€â”€â”€â”€
            text = str(row.get("Question", ""))
            parts = re.split(r"\n(?=[A-D]\))", text)
            q_prompt = parts[0].strip()
            opts: dict[str, str] = {}
            for part in parts[1:]:
                m = re.match(r"^([A-D])\)\s*(.*)", part.strip(), re.DOTALL)
                if m:
                    opts[m.group(1)] = m.group(2).strip()
            questions.append({
                "id": idx,
                "title": _safe(row, "Question No", default=f"Q{idx}"),
                "marks": int(float(_safe(row, "Marks", default="1"))),
                "co": _safe(row, "CO", default=""),
                "lo": _safe(row, "LO", default=""),
                "knowledge_type": _safe(row, "Knowledge Type", default=""),
                "category": _safe(row, "Domain", "Category", default=""),
                "rbt_level": _safe(row, "RBT level", "RBT_Level", default=""),
                "text": q_prompt,
                "question_type": "Objective",
                "options": opts,
                "correct_option": _safe(row, "Answer Key", "Correct_Option", default=""),
                "guidelines": [],
            })

        else:
            # â”€â”€ Subjective â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            questions.append({
                "id": idx,
                "title": _safe(row, "Question No", default=f"Q{idx}"),
                "marks": int(float(_safe(row, "Marks", default="10"))),
                "co": _safe(row, "CO", default=""),
                "lo": _safe(row, "LO", default=""),
                "knowledge_type": _safe(row, "Knowledge Type", default=""),
                "category": _safe(row, "Domain", "Category", default=""),
                "rbt_level": _safe(row, "RBT level", "RBT_Level", default=""),
                "text": _safe(row, "Question", default=""),
                "question_type": "Subjective",
                "options": {},
                "correct_option": "",
                "guidelines": [
                    "Read the question carefully.",
                    "Answer in your own words.",
                    "Support your answer with relevant points.",
                ],
            })

    print(f"[QP] Loaded {len(questions)} questions from {filepath.name}")
    return questions


def _get_upload_dir() -> Path:
    """Return Reflex's upload directory."""
    try:
        p = rx.get_upload_dir()
        return Path(str(p))
    except Exception:
        return Path("uploaded_files")


def _strip_html(html: str) -> str:
    """Best-effort plain-text extraction from the rich-text editor's HTML,
    used only for word-counting / 'has the candidate answered this
    question yet' checks â€” never for grading or storage."""
    if not html:
        return ""
    text = re.sub(r"<(br|/div|/p|/li)\s*/?>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    return text.strip()


# In-memory global store that persists across sessions, refreshes, and page navigation.
# Key: f"{candidate_id}::{assessment_name}::{test_name}"
# Value: dict with keys:
#   "candidate_id", "assessment_name", "test_name", "status" ("In Progress"|"Submitted"|"Disqualified"),
#   "violation_count" (0..3), "submitted_at", "submission_receipt", "answers", "marked_for_review"
PERSISTED_CANDIDATE_TEST_DATA: dict[str, dict] = {}


class CandidateState(rx.State):
    # Candidate identity (emp_id or email)
    candidate_id: str = "CAND-2031"

    # â”€â”€ Active Test Session Metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    active_assessment_name: str = "Quality"
    active_test_name: str = "Formative 1"

    # Test Session State
    current_question_index: int = 0  # Always start at Question 1
    total_time_seconds: int = 5400  # 01:30:00 (90 minutes)
    time_display: str = "01:30:00"
    is_time_expired: bool = False
    timer_session_id: int = 0

    # Candidate Answers â€” dictionary mapping question ID (str) to answer
    # HTML (rich-text content from the answer editor) for Subjective questions.
    answers: dict[str, str] = {}

    # MCQ Answers â€” dictionary mapping question ID (str) to selected option letter
    # e.g. {"1": "A", "3": "C"}  for Objective questions.
    mcq_answers: dict[str, str] = {}

    # Marked for Review question IDs (list of ints)
    marked_for_review: list[int] = []

    # Auto-save indicator text
    auto_save_status: str = ""

    # â”€â”€ Question Navigation Panel State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    nav_filter: str = "all"  # "all" | "objective" | "subjective"
    show_instructions: bool = True

    # â”€â”€ Test completion stores for dashboard reactivity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Structure: { assessment_name: { test_name: timestamp } }
    # Mirrors FacilitatorState.question_papers for seamless .contains() checks in Reflex
    submitted_tests: dict[str, dict[str, str]] = {}
    disqualified_tests: dict[str, dict[str, str]] = {}

    # â”€â”€ Proctoring State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    is_fullscreen: bool = True
    is_tab_locked: bool = True
    camera_active: bool = True
    mic_active: bool = True
    violation_count: int = 0
    max_violations: int = 3
    show_violation_modal: bool = False
    violation_warning_msg: str = ""

    # â”€â”€ Submission State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    show_submit_dialog: bool = False
    is_test_submitted: bool = False
    submission_receipt: str = ""
    submitted_at: str = ""

    # â”€â”€ Score snapshot (populated on dashboard load from FacilitatorState) â”€â”€
    # Flat dicts with composite keys to work cleanly inside rx.foreach vars.
    # Key for test-level: "AssessmentName::TestName"
    candidate_test_scores: dict[str, str] = {}      # -> score_str e.g. "72%" or "-"
    candidate_test_evaluated: dict[str, bool] = {}  # -> True / False

    # â”€â”€ Candidate Feedback State (Post-submission) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    show_candidate_feedback_modal: bool = False
    candidate_feedback_questions: list[dict] = []
    candidate_feedback_answers: dict[str, str] = {}
    candidate_feedback_error: str = ""
    saved_candidate_feedbacks: dict[str, dict] = {}

    # â”€â”€ Candidate Identity Helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async def _get_current_candidate_id(self) -> str:
        try:
            auth = await self.get_state(AuthState)
            cid = str(auth.candidate_emp_id or auth.candidate_email or "").strip()
            if cid:
                self.candidate_id = cid
                return cid
        except Exception:
            pass
        return self.candidate_id or "CAND-2031"

    def _save_current_test_record(self, status: str = ""):
        cand_id = self.candidate_id or "CAND-2031"
        key = f"{cand_id}::{self.active_assessment_name}::{self.active_test_name}"
        existing = PERSISTED_CANDIDATE_TEST_DATA.get(key, {})

        curr_status = status or existing.get("status", "In Progress")
        if existing.get("status") in ("Submitted", "Disqualified") and not status:
            curr_status = existing.get("status")

        PERSISTED_CANDIDATE_TEST_DATA[key] = {
            "candidate_id": cand_id,
            "assessment_name": self.active_assessment_name,
            "test_name": self.active_test_name,
            "status": curr_status,
            "violation_count": min(self.violation_count, self.max_violations),
            "submitted_at": self.submitted_at or existing.get("submitted_at", ""),
            "submission_receipt": self.submission_receipt or existing.get("submission_receipt", ""),
            "answers": dict(self.answers),
            "mcq_answers": dict(self.mcq_answers),
            "marked_for_review": list(self.marked_for_review),
        }

    # â”€â”€ Computed Variables â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @rx.var
    def current_question(self) -> dict:
        qs = LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])
        if not qs:
            return {}
        idx = self.current_question_index
        if 0 <= idx < len(qs):
            return qs[idx]
        return qs[0]

    @rx.var
    def current_question_number(self) -> int:
        return self.current_question_index + 1

    @rx.var
    def total_questions(self) -> int:
        return len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []))

    @rx.var
    def current_answer_text(self) -> str:
        qid_str = str(self.current_question_number)
        return self.answers.get(qid_str, "")

    @rx.var
    def current_word_count(self) -> int:
        text = _strip_html(self.current_answer_text)
        if not text:
            return 0
        return len(text.split())

    @rx.var
    def is_current_marked(self) -> bool:
        return self.current_question_number in self.marked_for_review

    @rx.var
    def answered_count(self) -> int:
        count = 0
        for q in LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []):
            qid_str = str(q["id"])
            if q.get("question_type") == "Objective":
                # MCQ: answered if an option has been selected
                if self.mcq_answers.get(qid_str, "").strip():
                    count += 1
            else:
                if _strip_html(self.answers.get(qid_str, "")).strip():
                    count += 1
        return count

    @rx.var
    def unanswered_count(self) -> int:
        return self.total_questions - self.answered_count

    @rx.var
    def marked_count(self) -> int:
        return len(self.marked_for_review)

    @rx.var
    def current_guidelines(self) -> list[str]:
        q = self.current_question
        return q.get("guidelines", [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ])

    @rx.var
    def current_question_type(self) -> str:
        """Returns 'Objective' or 'Subjective' for the current question."""
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("question_type", "Subjective"))
        return "Subjective"

    @rx.var
    def current_mcq_answer(self) -> str:
        """Returns the selected option letter (e.g. 'A') for the current MCQ question."""
        qid_str = str(self.current_question_number)
        return self.mcq_answers.get(qid_str, "")

    @rx.var
    def current_option_a(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("options", {}).get("A", ""))
        return ""

    @rx.var
    def current_option_b(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("options", {}).get("B", ""))
        return ""

    @rx.var
    def current_option_c(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("options", {}).get("C", ""))
        return ""

    @rx.var
    def current_option_d(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("options", {}).get("D", ""))
        return ""

    # â”€â”€ Question Navigation Computed Vars â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @rx.var
    def nav_questions(self) -> list[dict]:
        """All uploaded questions for the navigation panel â€” no type filtering."""
        items = []
        curr = self.current_question_number
        marked_set = set(self.marked_for_review)

        for q in LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []):
            q_id = q["id"]
            q_type = q.get("question_type", "Subjective")
            qid_str = str(q_id)
            is_curr = (q_id == curr)
            is_marked = (q_id in marked_set)

            if q_type == "Objective":
                is_answered = bool(self.mcq_answers.get(qid_str, "").strip())
            else:
                is_answered = bool(_strip_html(self.answers.get(qid_str, "")).strip())

            if is_curr:
                status = "current"
            elif is_marked:
                status = "marked"
            elif is_answered:
                status = "answered"
            else:
                status = "unanswered"

            items.append({
                "id": q_id,
                "number": str(q_id),
                "type": q_type,
                "status": status,
                "is_current": is_curr,
                "is_marked": is_marked,
                "is_answered": is_answered,
            })
        return items

    @rx.var
    def total_nav_count(self) -> int:
        return len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []))

    @rx.var
    def objective_nav_count(self) -> int:
        return sum(1 for q in LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []) if q.get("question_type") == "Objective")

    @rx.var
    def subjective_nav_count(self) -> int:
        return sum(1 for q in LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []) if q.get("question_type") == "Subjective")

    @rx.var
    def active_test_key(self) -> str:
        """Composite key for test lookup."""
        return f"{self.active_assessment_name}__{self.active_test_name}"

    @rx.var
    def display_test_name(self) -> str:
        """Dynamically return the active test name, replacing any legacy 'Test 1' with the assessment's configured test."""
        name = self.active_test_name
        if name and name != "Test 1":
            return name
        try:
            for a in AdminState.assessments:
                if a.get("name") == self.active_assessment_name:
                    tests = a.get("tests", [])
                    if tests:
                        return str(tests[0])
                    if a.get("final_test"):
                        return str(a.get("final_test"))
        except Exception:
            pass
        return "Formative 1"

    @rx.var
    def is_disqualified(self) -> bool:
        """True when the current test session was terminated for violations."""
        return self.active_test_name in self.disqualified_tests.get(self.active_assessment_name, {})

    @rx.var
    def is_last_question(self) -> bool:
        """True when the candidate is on the final question."""
        return self.current_question_index >= len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])) - 1

    # â”€â”€ Question metadata computed vars (CO / LO / RBT / Marks) â”€â”€â”€â”€â”€â”€â”€
    # Access LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []) directly (cannot chain .get() on an rx.var result)
    @rx.var
    def current_question_marks(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            v = LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("marks", "")
            return str(v) if v != "" else ""
        return ""

    @rx.var
    def current_question_co(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("co", ""))
        return ""

    @rx.var
    def current_question_lo(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("lo", ""))
        return ""

    @rx.var
    def current_question_rbt(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            return str(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])[idx].get("rbt_level", ""))
        return ""

    # â”€â”€ Timer & Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @rx.event(background=True)
    async def run_timer(self):
        current_session = self.timer_session_id
        while True:
            await asyncio.sleep(1)
            async with self:
                if self.timer_session_id != current_session:
                    return
                if self.is_test_submitted or self.is_time_expired:
                    return
                if self.total_time_seconds <= 0:
                    await self.handle_time_expired()
                    return
                self.total_time_seconds -= 1
                h = self.total_time_seconds // 3600
                m = (self.total_time_seconds % 3600) // 60
                s = self.total_time_seconds % 60
                self.time_display = f"{h:02d}:{m:02d}:{s:02d}"

    async def on_dashboard_load(self):
        """Called when candidate dashboard loads to sync persistent submission & violation records."""
        cand_id = await self._get_current_candidate_id()
        subs: dict[str, dict[str, str]] = {}
        dqs: dict[str, dict[str, str]] = {}
        for key, rec in PERSISTED_CANDIDATE_TEST_DATA.items():
            if rec.get("candidate_id") == cand_id:
                a_name = rec.get("assessment_name", "")
                t_name = rec.get("test_name", "")
                if rec.get("status") == "Submitted":
                    if a_name not in subs:
                        subs[a_name] = {}
                    subs[a_name][t_name] = rec.get("submitted_at", "")
                elif rec.get("status") == "Disqualified":
                    if a_name not in dqs:
                        dqs[a_name] = {}
                    dqs[a_name][t_name] = rec.get("submitted_at", "")
        self.submitted_tests = subs
        self.disqualified_tests = dqs
        await self.refresh_candidate_scores()

    async def refresh_candidate_scores(self):
        """Read evaluation results + weightages from FacilitatorState and build
        a per-assessment score snapshot for the currently logged-in candidate.
        Only reads data â€” never writes to any submission or proctoring store."""
        from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
        from ai_hybrid_evaluator.state.admin_state import AdminState as _AdminState

        cand_id = self.candidate_id or "CAND-2031"

        try:
            fac_st = await self.get_state(FacilitatorState)
            admin_st = await self.get_state(_AdminState)
        except Exception:
            return

        results = fac_st.real_ai_results_per_candidate  # {"Name (ID):test_name": {...}}
        new_test_scores: dict[str, str] = {}
        new_test_evaluated: dict[str, bool] = {}

        for a in admin_st.assessments:
            asmn = a.get("name", "")
            if not asmn:
                continue
            # Only process assessments the candidate is assigned to
            if cand_id not in a.get("assigned_candidates", []):
                continue

            all_test_names: list[str] = list(a.get("tests", []))
            final_test = a.get("final_test", "")
            if final_test:
                all_test_names.append(final_test)

            if not all_test_names:
                continue

            # Build per-test score entries
            for t_name in all_test_names:
                flat_key = f"{asmn}::{t_name}"
                norm: float | None = None
                for rkey, rval in results.items():
                    # Key format: "CandidateName (EMP-ID):test_name"
                    parts = rkey.split(":")
                    if len(parts) < 2:
                        continue
                    r_cand_label = parts[0].strip()
                    r_test_name = ":".join(parts[1:]).strip()
                    if r_test_name != t_name:
                        continue
                    if cand_id in r_cand_label:
                        try:
                            norm = FacilitatorState._calculate_normalized_score(rval)
                        except Exception:
                            norm = None
                        break
                if norm is not None:
                    score_int = int(round(norm))
                    new_test_scores[flat_key] = f"{score_int}%"
                    new_test_evaluated[flat_key] = True
                else:
                    new_test_scores[flat_key] = "-"
                    new_test_evaluated[flat_key] = False

        self.candidate_test_scores = new_test_scores
        self.candidate_test_evaluated = new_test_evaluated


    async def on_test_page_load(self):
        """Called when candidate test page loads to ensure timer is active or lock submitted/disqualified test."""
        if self.active_test_name == "Test 1" or not self.active_test_name:
            try:
                admin_st = await self.get_state(AdminState)
                for a in admin_st.assessments:
                    if a.get("name") == self.active_assessment_name:
                        t_list = a.get("tests", [])
                        if t_list:
                            self.active_test_name = t_list[0]
                        elif a.get("final_test"):
                            self.active_test_name = a.get("final_test")
                        break
            except Exception:
                self.active_test_name = "Formative 1"

        cand_id = await self._get_current_candidate_id()
        key = f"{cand_id}::{self.active_assessment_name}::{self.active_test_name}"
        record = PERSISTED_CANDIDATE_TEST_DATA.get(key)

        if record:
            status = record.get("status")
            if status == "Submitted":
                self.is_test_submitted = True
                self.submitted_at = record.get("submitted_at", "")
                self.submission_receipt = record.get("submission_receipt", "")
                self.show_submit_dialog = False
                self.show_violation_modal = False
                return
            elif status == "Disqualified":
                self.is_test_submitted = True
                self.violation_count = self.max_violations
                self.submitted_at = record.get("submitted_at", "")
                self.submission_receipt = record.get("submission_receipt", "")
                self.show_submit_dialog = False
                self.show_violation_modal = False
                return
            else:
                # In progress: restore violation count, answers, marked list
                self.violation_count = min(record.get("violation_count", 0), self.max_violations)
                if record.get("answers"):
                    self.answers = dict(record.get("answers"))
                if record.get("mcq_answers"):
                    self.mcq_answers = dict(record.get("mcq_answers"))
                if record.get("marked_for_review"):
                    self.marked_for_review = list(record.get("marked_for_review"))

        # Always start at Question 1 (index 0) â€” even for In Progress tests
        self.current_question_index = 0

        if not self.is_test_submitted and not self.is_time_expired:
            self.timer_session_id += 1
            return [CandidateState.run_timer, self._restore_rte_script()]

    async def handle_time_expired(self):
        """Auto-submit the test when timer reaches 00:00:00."""
        now = datetime.now()
        self.is_test_submitted = True
        self.is_time_expired = True
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.submitted_at = now.strftime("%B %d, %Y at %I:%M %p")
        self.submission_receipt = f"SUB-{now.strftime('%Y%m%d')}-{self.active_test_name.replace(' ', '')}-9841"

        subs = {k: dict(v) for k, v in self.submitted_tests.items()}
        if self.active_assessment_name not in subs:
            subs[self.active_assessment_name] = {}
        subs[self.active_assessment_name][self.active_test_name] = now.isoformat()
        self.submitted_tests = subs

        self._save_current_test_record(status="Submitted")

    async def start_test(self, assessment_name: str, test_name: str):
        """Launch the test session and navigate to /candidate/test. Blocks already submitted tests."""
        cand_id = await self._get_current_candidate_id()
        key = f"{cand_id}::{assessment_name}::{test_name}"
        record = PERSISTED_CANDIDATE_TEST_DATA.get(key)

        if record:
            if record.get("status") == "Submitted":
                return rx.toast.info("This test has already been submitted and cannot be retaken.")
            if record.get("status") == "Disqualified":
                return rx.toast.error("This test was terminated due to proctoring violations and cannot be retaken.")

        self.active_assessment_name = assessment_name
        self.active_test_name = test_name

        # ── Load questions from the Facilitator-uploaded file ────────────
        # Import here to avoid circular imports; FacilitatorState lives in the same process.
        q_key = f"{assessment_name}::{test_name}"
        if q_key not in LOADED_TEST_QUESTIONS:
            try:
                from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState as FS
                fac = await self.get_state(FS)
                filename = fac.question_papers.get(assessment_name, {}).get(test_name, "")
                if filename:
                    upload_dir = _get_upload_dir()
                    filepath = upload_dir / filename
                    qs = _load_questions_from_file(filepath)
                    if qs:
                        LOADED_TEST_QUESTIONS[q_key] = qs
                        print(f"[QP] Loaded {len(qs)} questions for {q_key} from {filename}")
                    else:
                        print(f"[QP] WARNING: No questions loaded for {q_key} from {filename}")
                        LOADED_TEST_QUESTIONS[q_key] = []
                else:
                    print(f"[QP] WARNING: No QP uploaded for {q_key}")
                    LOADED_TEST_QUESTIONS[q_key] = []
            except Exception as e:
                print(f"[QP] ERROR loading questions for {q_key}: {e}")
                LOADED_TEST_QUESTIONS[q_key] = []

        # Always start at Question 1 (index 0)
        self.current_question_index = 0
        self.is_test_submitted = False
        self.show_candidate_feedback_modal = False
        self.is_time_expired = False
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.auto_save_status = "Auto-saved"
        self.total_time_seconds = 5400  # 01:30:00
        self.time_display = "01:30:00"
        self.is_fullscreen = True

        if record:
            self.violation_count = min(record.get("violation_count", 0), self.max_violations)
            self.answers = dict(record.get("answers", {}))
            self.mcq_answers = dict(record.get("mcq_answers", {}))
            self.marked_for_review = list(record.get("marked_for_review", []))
        else:
            self.violation_count = 0
            self.answers = {}
            self.mcq_answers = {}
            self.marked_for_review = []
            self._save_current_test_record(status="In Progress")

        self.timer_session_id += 1
        return [rx.redirect("/candidate/test"), CandidateState.run_timer]


    def _restore_rte_script(self):
        """Return a call_script that pushes the currently saved answer HTML
        into the contenteditable editor AND sets the data-* attributes on the
        relay input so the localStorage helpers know the current
        candidate/assessment/test/question context.
        Called after every question-navigation action."""
        qid_str = str(self.current_question_number)
        saved_html = self.answers.get(qid_str, "")
        # Escape for safe JS string embedding
        safe_html = (
            saved_html
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace("\n", "\\n")
            .replace("\r", "")
        )
        safe_cid  = (self.candidate_id or "unknown").replace("'", "\\'")
        safe_asmn = self.active_assessment_name.replace("'", "\\'")
        safe_test = self.active_test_name.replace("'", "\\'")
        js = f"""
(function() {{
    var relay = document.getElementById('rte-relay');
    if (relay) {{
        relay.dataset.candidateId = '{safe_cid}';
        relay.dataset.assessment  = '{safe_asmn}';
        relay.dataset.testName    = '{safe_test}';
        relay.dataset.questionId  = '{qid_str}';
        relay.dataset.saved       = '{safe_html}';
    }}
    if (window.__rteRestoreAnswer) {{
        window.__rteRestoreAnswer('{safe_html}', '{qid_str}');
    }}
}})();
"""
        return rx.call_script(js)

    def set_question_index(self, index: int):
        if 0 <= index < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])):
            self.current_question_index = index
            self._save_current_test_record()
            return self._restore_rte_script()

    def jump_to_question(self, q_num: int):
        """Immediately open the specified question number (1-based index)."""
        return self.set_question_index(q_num - 1)

    def set_nav_filter(self, f: str):
        self.nav_filter = f

    def toggle_instructions(self):
        self.show_instructions = not self.show_instructions

    def next_question(self):
        if self.current_question_index < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])) - 1:
            self.current_question_index += 1
            return self._restore_rte_script()

    def prev_question(self):
        if self.current_question_index > 0:
            self.current_question_index -= 1
            return self._restore_rte_script()

    def update_answer(self, text: str):
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        qid_str = str(self.current_question_number)
        new_answers = dict(self.answers)
        new_answers[qid_str] = text
        self.answers = new_answers
        self.auto_save_status = "Auto-saved"
        self._save_current_test_record()

    def select_mcq_option(self, option: str):
        """Save the selected MCQ option for the current Objective question."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        qid_str = str(self.current_question_number)
        new_mcq = dict(self.mcq_answers)
        new_mcq[qid_str] = option
        self.mcq_answers = new_mcq
        self.auto_save_status = "Auto-saved"
        self._save_current_test_record()

    def clear_mcq_answer(self):
        """Clear the MCQ answer for the current Objective question."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        qid_str = str(self.current_question_number)
        new_mcq = dict(self.mcq_answers)
        new_mcq.pop(qid_str, None)
        self.mcq_answers = new_mcq
        self.auto_save_status = "Auto-saved"
        self._save_current_test_record()

    def set_answer_html(self, html: str):
        """Save the rich-text HTML produced by the answer editor's toolbar/typing
        for the currently active question.
        Guard: never overwrite a non-empty saved answer with an empty value
        (prevents navigation/rerender clearing existing answers)."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        qid_str = str(self.current_question_number)
        # Guard: do not overwrite a non-empty saved answer with empty HTML
        existing = self.answers.get(qid_str, "")
        if not html.strip() and _strip_html(existing).strip():
            return
        self.auto_save_status = "Saving..."
        try:
            new_answers = dict(self.answers)
            new_answers[qid_str] = html
            self.answers = new_answers
            self._save_current_test_record()
            self.auto_save_status = "Auto-saved"
        except Exception:
            self.auto_save_status = "Save failed"

    def toggle_mark_for_review(self):
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        qid = self.current_question_number
        current_list = list(self.marked_for_review)
        if qid in current_list:
            # Unmark: remove only this question
            self.marked_for_review = [q for q in current_list if q != qid]
        else:
            # Mark: add only if not already present
            if qid not in current_list:
                self.marked_for_review = current_list + [qid]
        self._save_current_test_record()

    def save_and_next_question(self):
        """Explicitly save the current answer then advance to the next question.
        Used by the 'Save & Next' button. Never deletes existing answers."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        # Persist current answers (already in state via set_answer_html)
        self._save_current_test_record()
        self.auto_save_status = "Auto-saved"
        if self.current_question_index < len(LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", [])) - 1:
            self.current_question_index += 1
            return self._restore_rte_script()

    def _record_violation(self, reason: str) -> bool:
        """Increment violation counter (strictly capped at max_violations = 3).
        Returns True if the test must now be terminated (reached 3/3)."""
        if self.violation_count >= self.max_violations:
            self.violation_count = self.max_violations
            return True

        self.violation_count += 1
        self.violation_warning_msg = (
            f"Warning {self.violation_count} of {self.max_violations}: {reason} "
            f"Your assessment session is monitored."
        )
        self._save_current_test_record()
        return self.violation_count >= self.max_violations

    def trigger_proctoring_warning(self):
        """Simulate a tab switch or screen unfocus violation."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        terminated = self._record_violation("Tab switching or window unfocus detected!")
        if terminated:
            self._terminate_for_violations()
        else:
            self.show_violation_modal = True

    def dismiss_violation_modal(self):
        if not self.is_disqualified:
            self.show_violation_modal = False

    def exit_fullscreen(self):
        self.is_fullscreen = False
        if not self.is_test_submitted and not self.is_time_expired and not self.is_disqualified:
            terminated = self._record_violation("Fullscreen exit detected! You must remain in fullscreen mode during the examination.")
            if terminated:
                self._terminate_for_violations()
            else:
                self.show_violation_modal = True
        return rx.call_script("if (document.fullscreenElement) { document.exitFullscreen().catch(function(e){console.warn(e);}); }")

    def handle_fullscreen_exited(self):
        """Detected when browser exits fullscreen."""
        if not self.is_test_submitted and not self.is_time_expired and not self.is_disqualified:
            if self.is_fullscreen:
                self.is_fullscreen = False
                terminated = self._record_violation("Fullscreen exit detected! You must remain in fullscreen mode during the examination.")
                if terminated:
                    self._terminate_for_violations()
                else:
                    self.show_violation_modal = True

    def _terminate_for_violations(self):
        """Auto-terminate the test when max violations (3/3) are reached."""
        now = datetime.now()
        self.violation_count = self.max_violations
        now_str = now.isoformat()

        # Update disqualified_tests nested dict
        dqs = {k: dict(v) for k, v in self.disqualified_tests.items()}
        if self.active_assessment_name not in dqs:
            dqs[self.active_assessment_name] = {}
        dqs[self.active_assessment_name][self.active_test_name] = now_str
        self.disqualified_tests = dqs

        self.is_test_submitted = True
        self.show_violation_modal = True
        self.submitted_at = now.strftime("%B %d, %Y at %I:%M %p")
        self.submission_receipt = f"DQ-{now.strftime('%Y%m%d')}-{self.active_test_name.replace(' ', '')}-VIOLATION"
        self.violation_warning_msg = (
            f"Warning {self.max_violations} of {self.max_violations}: "
            f"You have reached the maximum allowed proctoring violations ({self.max_violations} of {self.max_violations}). "
            "Your test has been terminated and flagged as Disqualified."
        )
        self._save_current_test_record(status="Disqualified")

    def handle_fullscreen_entered(self):
        """Detected when browser enters fullscreen."""
        self.is_fullscreen = True

    # â”€â”€ Submission Flow â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def open_submit_dialog(self):
        if not self.is_test_submitted and not self.is_time_expired and not self.is_disqualified:
            self.show_submit_dialog = True

    def close_submit_dialog(self):
        self.show_submit_dialog = False

    def confirm_submit_test(self):
        """Submit the assessment and save the candidate answers as Excel."""
        now = datetime.now()

        cand_id = self.candidate_id or "CAND-2031"
        try:
            save_candidate_response(
                candidate_id=cand_id,
                candidate_name=cand_id,
                assessment_name=self.active_assessment_name,
                test_name=self.active_test_name,
                questions=LOADED_TEST_QUESTIONS.get(f"{self.active_assessment_name}::{self.active_test_name}", []),
                answers=self.answers,
            )
        except Exception as e:
            print(f"Error saving candidate response: {e}")

        self.is_test_submitted = True
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.submitted_at = now.strftime("%B %d, %Y at %I:%M %p")
        self.submission_receipt = f"SUB-{now.strftime('%Y%m%d')}-{self.active_test_name.replace(' ', '')}-9841"

        subs = {k: dict(v) for k, v in self.submitted_tests.items()}
        if self.active_assessment_name not in subs:
            subs[self.active_assessment_name] = {}
        subs[self.active_assessment_name][self.active_test_name] = now.isoformat()
        self.submitted_tests = subs

        self._save_current_test_record(status="Submitted")
        self.show_candidate_feedback_modal = False
        return rx.toast.success("Assessment submitted successfully!", duration=4000)

    def return_to_dashboard(self):
        """Navigate back to the candidate dashboard after test submission.

        Always exits browser fullscreen first so the dashboard never
        inherits fullscreen state from a completed test.  Because
        is_test_submitted is True before this is called, the
        fullscreenchange listener will NOT record a proctoring violation.
        """
        self.show_submit_dialog = False
        self.show_violation_modal = False
        # Reset fullscreen flag so the next test starts fresh
        self.is_fullscreen = False
        return [
            rx.call_script(
                "if (document.fullscreenElement) {"
                "  document.exitFullscreen().catch(function(e){ console.warn(e); });"
                "}"
            ),
            rx.redirect("/candidate/dashboard"),
        ]

    # â”€â”€ Candidate Test Feedback Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def _get_candidate_feedback_file_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "candidate_feedbacks.json"

    def _load_saved_candidate_feedbacks(self) -> dict[str, dict]:
        fp = CandidateState._get_candidate_feedback_file_path()
        if fp.exists():
            try:
                import json
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _persist_candidate_feedbacks(self):
        fp = CandidateState._get_candidate_feedback_file_path()
        try:
            import json
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.saved_candidate_feedbacks, f, indent=2)
        except Exception:
            pass

    def open_candidate_feedback_form(self):
        """Open the Candidate Feedback modal ready for the dynamic Admin-created form.

        FRONTEND INTEGRATION POINT:
        Future backend flow:
            Admin creates Candidate Feedback Form
            -> Backend stores the form
            -> Candidate submits Assessment + Test
            -> Backend provides the Admin-created form
            -> Existing Candidate Feedback modal displays dynamic questions
            -> Candidate submits responses.
        Until the backend provides the form data, self.candidate_feedback_questions remains empty.
        """
        self.candidate_feedback_questions = []
        self.candidate_feedback_answers = {}
        self.candidate_feedback_error = ""
        self.show_candidate_feedback_modal = True

    def skip_candidate_feedback(self):
        """Close feedback modal and return to candidate dashboard."""
        self.show_candidate_feedback_modal = False
        self.candidate_feedback_questions = []
        self.candidate_feedback_answers = {}
        self.candidate_feedback_error = ""
        return self.return_to_dashboard()

    def set_candidate_feedback_answer(self, question_id: str, answer: str):
        answers = dict(self.candidate_feedback_answers)
        answers[question_id] = answer
        self.candidate_feedback_answers = answers
        self.candidate_feedback_error = ""

    async def submit_candidate_test_feedback(self):
        """Save dynamic feedback when form data is provided by the backend."""
        # Do not allow submission when no form data is available
        if not self.candidate_feedback_questions:
            return

        missing_required = [
            question for question in self.candidate_feedback_questions
            if question.get("required", False)
            and not self.candidate_feedback_answers.get(question["id"], "").strip()
        ]
        if missing_required:
            self.candidate_feedback_error = "Please complete all required questions before submitting."
            return

        cand_id = await self._get_current_candidate_id()
        cand_name = "Candidate"
        try:
            auth = await self.get_state(AuthState)
            cand_name = auth.candidate_name or "Candidate"
        except Exception:
            pass

        asmn = self.active_assessment_name or "Quality"
        test_name = self.active_test_name or "Formative 1"

        if not self.saved_candidate_feedbacks:
            self.saved_candidate_feedbacks = self._load_saved_candidate_feedbacks()

        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        key = f"{asmn}:{test_name}:{cand_id}"
        updated = dict(self.saved_candidate_feedbacks)
        updated[key] = {
            "assessment": asmn,
            "test": test_name,
            "candidate_id": cand_id,
            "candidate_name": cand_name,
            "answers": dict(self.candidate_feedback_answers),
            "submitted_at": now_str,
        }
        self.saved_candidate_feedbacks = updated
        self._persist_candidate_feedbacks()

        self.show_candidate_feedback_modal = False
        self.candidate_feedback_questions = []
        self.candidate_feedback_answers = {}
        self.candidate_feedback_error = ""

        yield rx.toast.success("Feedback submitted successfully. Thank you!")
        for action in self.return_to_dashboard():
            yield action


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Candidate Profile State
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class CandidateProfileState(rx.State):
    """Candidate Profile state with photo upload and organization details."""

    # 1. Employee Information
    profile_photo_url: str = ""
    full_name: str = "Priya Sharma"
    emp_id: str = "CAND-2031"
    email: str = "priya.sharma@genaievaluator.com"
    phone: str = "+91 98765 43210"
    location: str = "Bangalore, India"
    date_of_joining: str = "2024-06-15"
    employment_status: str = "Active"

    # 2. Organization Details
    company_bu: str = "TVS Motor Company"
    department: str = "Quality Assurance & Testing"
    designation: str = "Senior Quality Engineer"
    grade_level: str = "L3 - Senior Associate"
    reporting_manager: str = "Ravi Kumar (Lead Evaluator)"
    work_location: str = "TVS Motor Plant, Hosur Facility, Block C"

    # Option lists for selects
    employment_status_options: list[str] = ["Active", "On Leave", "Inactive"]
    department_options: list[str] = [
        "Quality Assurance & Testing",
        "Research & Development (R&D)",
        "Manufacturing & Production",
        "Supply Chain & Operations",
        "IT & Digital Transformation",
        "Product Design & Engineering",
        "Human Resources",
        "Other",
    ]
    designation_options: list[str] = [
        "Graduate Engineering Trainee",
        "Associate Quality Engineer",
        "Senior Quality Engineer",
        "Quality Lead / Specialist",
        "Software Engineer",
        "Senior Software Engineer",
        "Manufacturing Specialist",
        "Other",
    ]
    grade_options: list[str] = [
        "E1 - Entry Level",
        "E2 - Executive",
        "L1 - Associate",
        "L2 - Professional",
        "L3 - Senior Associate",
        "L4 - Principal / Lead",
        "M1 - Managerial",
    ]

    # Setters
    def set_full_name(self, v: str): self.full_name = v
    def set_emp_id(self, v: str): self.emp_id = v
    def set_email(self, v: str): self.email = v
    def set_phone(self, v: str): self.phone = v
    def set_location(self, v: str): self.location = v
    def set_date_of_joining(self, v: str): self.date_of_joining = v
    def set_employment_status(self, v: str): self.employment_status = v

    def set_company_bu(self, v: str): self.company_bu = v
    def set_department(self, v: str): self.department = v
    def set_designation(self, v: str): self.designation = v
    def set_grade_level(self, v: str): self.grade_level = v
    def set_reporting_manager(self, v: str): self.reporting_manager = v
    def set_work_location(self, v: str): self.work_location = v

    async def load_profile(self):
        """Load candidate profile from shared store."""
        try:
            auth = await self.get_state(AuthState)
            if auth.candidate_emp_id:
                self.emp_id = auth.candidate_emp_id
        except Exception:
            pass

        cid = self.emp_id or "CAND-2031"
        prof = get_candidate_profile(
            cid,
            default_name=self.full_name or "Candidate",
            default_email=self.email,
        )
        self.full_name = prof.get("full_name", "")
        self.email = prof.get("email", "")
        self.phone = prof.get("phone", "")
        self.location = prof.get("location", "")
        self.profile_photo_url = prof.get("profile_photo_url", "")
        self.date_of_joining = prof.get("date_of_joining", "")
        self.employment_status = prof.get("employment_status", "Active")
        self.company_bu = prof.get("company_bu", "TVS Motor Company")
        self.department = prof.get("department", "Quality Assurance & Testing")
        self.designation = prof.get("designation", "Senior Quality Engineer")
        self.grade_level = prof.get("grade_level", "L3 - Senior Associate")
        self.reporting_manager = prof.get("reporting_manager", "Ravi Kumar (Lead Evaluator)")
        self.work_location = prof.get("work_location", "TVS Motor Plant, Hosur Facility, Block C")

    async def handle_photo_upload(self, files: list[rx.UploadFile]):
        """Upload and display the selected candidate profile image immediately."""
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
            safe_filename = f"candidate_photo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            with open(out_dir / safe_filename, "wb") as f:
                f.write(upload_data)
        except Exception:
            pass

        # Save photo to shared store
        save_candidate_profile(self.emp_id, {"profile_photo_url": self.profile_photo_url})
        return rx.toast.success(f"Profile photo updated: {file.filename}")

    async def save_profile(self):
        """Save candidate profile changes to shared store."""
        data = {
            "emp_id": self.emp_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "profile_photo_url": self.profile_photo_url,
            "date_of_joining": self.date_of_joining,
            "employment_status": self.employment_status,
            "company_bu": self.company_bu,
            "department": self.department,
            "designation": self.designation,
            "grade_level": self.grade_level,
            "reporting_manager": self.reporting_manager,
            "work_location": self.work_location,
        }
        save_candidate_profile(self.emp_id, data)
        return rx.toast.success("Profile saved successfully!")

