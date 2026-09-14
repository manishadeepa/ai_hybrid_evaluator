"""
Candidate State — manages candidate dashboard and active test environment session.
Includes mock questions, candidate answers, navigation, proctoring alerts, and submission flow.
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


MOCK_SUBJECTIVE_QUESTIONS = [
    {
        "id": 1,
        "title": "Machine Learning Fundamentals in Assessment",
        "marks": 10,
        "category": "Artificial Intelligence",
        "text": "Explain how supervised machine learning models can be trained to evaluate structured coding and technical assessment submissions.",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    },
    {
        "id": 2,
        "title": "Natural Language Processing for Subjective Grading",
        "marks": 10,
        "category": "NLP & Evaluation",
        "text": "Describe the architecture of Large Language Models (LLMs) used in evaluating semantic similarity between student answers and model answer keys.",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    },
    {
        "id": 3,
        "title": "Automated Evaluation Systems in Education",
        "marks": 10,
        "category": "GenAI Systems",
        "text": "Discuss the key advantages and limitations of using Artificial Intelligence in automated evaluation systems in education.",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    },
    {
        "id": 4,
        "title": "Quality Assurance in Model Output Verification",
        "marks": 10,
        "category": "Quality Assurance",
        "text": "How do human-in-the-loop (HITL) workflows ensure fairness, accountability, and reliability in automated AI grading pipelines?",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    },
    {
        "id": 5,
        "title": "Statistical Process Control & Capability Indices",
        "marks": 10,
        "category": "Quality Engineering",
        "text": "Explain the fundamental difference between Process Capability (Cp) and Process Performance (Cpk) in manufacturing quality assurance.",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    },
] + [
    {
        "id": i,
        "title": f"Technical Engineering & Quality Analysis — Part {i}",
        "marks": 10,
        "category": "Core Engineering",
        "text": f"Analyze the engineering parameters, failure modes, and mitigation strategies applicable to Section {i} of industrial manufacturing quality systems.",
        "guidelines": [
            "Your answer should be structured and clear.",
            "Support your points with relevant examples.",
            "Write in your own words.",
        ],
    }
    for i in range(6, 21)
]

QUESTION_PAPER_PATH = Path("uploaded_files") / "Question sheet.xlsx"


def load_question_paper_questions() -> list[dict]:
    """Load the candidate questions from the real Question Paper Excel file."""
    path_to_use = QUESTION_PAPER_PATH
    if not path_to_use.exists():
        alt = Path(__file__).resolve().parents[2] / "uploaded_files" / "Question sheet.xlsx"
        if alt.exists():
            path_to_use = alt

    try:
        df = pd.read_excel(path_to_use)
        questions = []
        for _, row in df.iterrows():
            q_num_str = str(row["Question No"]).replace("Q", "").strip()
            q_id = int(q_num_str) if q_num_str.isdigit() else len(questions) + 1
            questions.append({
                "id": q_id,
                "title": str(row["Question No"]),
                "marks": int(row["Marks"]) if pd.notna(row.get("Marks")) else 10,
                "co": str(row.get("CO", "")),
                "lo": str(row.get("LO", "")),
                "knowledge_type": str(row.get("Knowledge Type", "")),
                "category": str(row.get("Domain", "")),
                "rbt_level": str(row.get("RBT level", "")),
                "text": str(row.get("Question", "")),
                "guidelines": [
                    "Read the question carefully.",
                    "Answer in your own words.",
                    "Support your answer with relevant points.",
                ],
            })
        if questions:
            return questions
    except Exception as e:
        print(f"Error loading {path_to_use}: {e}")
    return MOCK_SUBJECTIVE_QUESTIONS


REAL_QUESTIONS = load_question_paper_questions()


def _strip_html(html: str) -> str:
    """Best-effort plain-text extraction from the rich-text editor's HTML,
    used only for word-counting / "has the candidate answered this
    question yet" checks — never for grading or storage."""
    if not html:
        return ""
    # Turn block-level breaks into spaces so words across separate
    # <div>/<p>/<br> lines don't get glued together when tags are stripped.
    text = re.sub(r"<(br|/div|/p|/li)\s*/?>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    return text.strip()


# ── Persistent test completion & violation store ──────────────────────────────
# In-memory global store that persists across sessions, refreshes, and page navigation.
# Key: f"{candidate_id}::{assessment_name}::{test_name}"
# Value: dict with keys:
#   "candidate_id", "assessment_name", "test_name", "status" ("In Progress"|"Submitted"|"Disqualified"),
#   "violation_count" (0..3), "submitted_at", "submission_receipt", "answers", "marked_for_review"
PERSISTED_CANDIDATE_TEST_DATA: dict[str, dict] = {}


class CandidateState(rx.State):
    # Candidate identity (emp_id or email)
    candidate_id: str = "CAND-2031"

    # ── Active Test Session Metadata ─────────────────────────────────────
    active_assessment_name: str = "Quality"
    active_test_name: str = "Formative 1"

    # Test Session State
    current_question_index: int = 0  # Always start at Question 1
    total_time_seconds: int = 5400  # 01:30:00 (90 minutes)
    time_display: str = "01:30:00"
    is_time_expired: bool = False
    timer_session_id: int = 0

    # Candidate Answers — dictionary mapping question ID (str) to answer
    # HTML (rich-text content from the answer editor).
    answers: dict[str, str] = {}

    # Marked for Review question IDs (list of ints)
    marked_for_review: list[int] = []

    # Auto-save indicator text
    auto_save_status: str = ""

    # ── Test completion stores for dashboard reactivity ───────────────────
    # Structure: { assessment_name: { test_name: timestamp } }
    # Mirrors FacilitatorState.question_papers for seamless .contains() checks in Reflex
    submitted_tests: dict[str, dict[str, str]] = {}
    disqualified_tests: dict[str, dict[str, str]] = {}

    # ── Proctoring State ────────────────────────────────────────────────
    is_fullscreen: bool = True
    is_tab_locked: bool = True
    camera_active: bool = True
    mic_active: bool = True
    violation_count: int = 0
    max_violations: int = 3
    show_violation_modal: bool = False
    violation_warning_msg: str = ""

    # ── Submission State ────────────────────────────────────────────────
    show_submit_dialog: bool = False
    is_test_submitted: bool = False
    submission_receipt: str = ""
    submitted_at: str = ""

    # ── Candidate Feedback State (Post-submission) ───────────────────────
    candidate_test_rating: int = 0
    candidate_test_feedback_text: str = ""
    candidate_test_feedback_tags: list[str] = []
    saved_candidate_feedbacks: dict[str, dict] = {}

    # ── Candidate Identity Helper ───────────────────────────────────────
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
            "marked_for_review": list(self.marked_for_review),
        }

    # ── Computed Variables ──────────────────────────────────────────────
    @rx.var
    def current_question(self) -> dict:
        if 0 <= self.current_question_index < len(REAL_QUESTIONS):
            return REAL_QUESTIONS[self.current_question_index]
        return REAL_QUESTIONS[0]

    @rx.var
    def current_question_number(self) -> int:
        return self.current_question_index + 1

    @rx.var
    def candidate_test_feedback_char_count(self) -> int:
        return len(self.candidate_test_feedback_text)

    @rx.var
    def total_questions(self) -> int:
        return len(REAL_QUESTIONS)

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
        for q in REAL_QUESTIONS:
            qid_str = str(q["id"])
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
        return self.current_question_index >= len(REAL_QUESTIONS) - 1

    # ── Question metadata computed vars (CO / LO / RBT / Marks) ───────
    # Access REAL_QUESTIONS directly (cannot chain .get() on an rx.var result)
    @rx.var
    def current_question_marks(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(REAL_QUESTIONS):
            v = REAL_QUESTIONS[idx].get("marks", "")
            return str(v) if v != "" else ""
        return ""

    @rx.var
    def current_question_co(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(REAL_QUESTIONS):
            return str(REAL_QUESTIONS[idx].get("co", ""))
        return ""

    @rx.var
    def current_question_lo(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(REAL_QUESTIONS):
            return str(REAL_QUESTIONS[idx].get("lo", ""))
        return ""

    @rx.var
    def current_question_rbt(self) -> str:
        idx = self.current_question_index
        if 0 <= idx < len(REAL_QUESTIONS):
            return str(REAL_QUESTIONS[idx].get("rbt_level", ""))
        return ""

    # ── Timer & Actions ──────────────────────────────────────────────────

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
                    self.handle_time_expired()
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
                if record.get("marked_for_review"):
                    self.marked_for_review = list(record.get("marked_for_review"))

        # Always start at Question 1 (index 0) — even for In Progress tests
        self.current_question_index = 0

        if not self.is_test_submitted and not self.is_time_expired:
            self.timer_session_id += 1
            return [CandidateState.run_timer, self._restore_rte_script()]

    def handle_time_expired(self):
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
        # Always start at Question 1 (index 0)
        self.current_question_index = 0
        self.is_test_submitted = False
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
            self.marked_for_review = list(record.get("marked_for_review", []))
        else:
            self.violation_count = 0
            self.answers = {}
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
        if 0 <= index < len(REAL_QUESTIONS):
            self.current_question_index = index
            return self._restore_rte_script()

    def next_question(self):
        if self.current_question_index < len(REAL_QUESTIONS) - 1:
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
        if self.current_question_index < len(REAL_QUESTIONS) - 1:
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

    # ── Submission Flow ─────────────────────────────────────────────────

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
                questions=REAL_QUESTIONS,
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

    # ── Candidate Test Feedback Methods ──────────────────────────────────
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

    def set_candidate_test_rating(self, rating: int):
        self.candidate_test_rating = rating

    def set_candidate_test_feedback_text(self, text: str):
        if len(text) <= 500:
            self.candidate_test_feedback_text = text
        else:
            self.candidate_test_feedback_text = text[:500]

    def toggle_candidate_feedback_tag(self, tag: str):
        tags = list(self.candidate_test_feedback_tags)
        if tag in tags:
            tags.remove(tag)
        else:
            tags.append(tag)
        self.candidate_test_feedback_tags = tags

    async def submit_candidate_test_feedback(self):
        """Save candidate feedback uniquely for Assessment + Test + Candidate, then return to dashboard."""
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
            "rating": self.candidate_test_rating,
            "feedback": self.candidate_test_feedback_text.strip(),
            "tags": list(self.candidate_test_feedback_tags),
            "submitted_at": now_str,
        }
        self.saved_candidate_feedbacks = updated
        self._persist_candidate_feedbacks()

        # Reset feedback fields
        self.candidate_test_rating = 0
        self.candidate_test_feedback_text = ""
        self.candidate_test_feedback_tags = []

        return self.return_to_dashboard()

    def skip_candidate_feedback(self):
        """Skip feedback and return to dashboard."""
        self.candidate_test_rating = 0
        self.candidate_test_feedback_text = ""
        self.candidate_test_feedback_tags = []
        return self.return_to_dashboard()


# ─────────────────────────────────────────────────────────────────────────────
# Candidate Profile State
# ─────────────────────────────────────────────────────────────────────────────

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