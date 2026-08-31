"""
Candidate State — manages candidate dashboard and active test environment session.
Includes mock questions, candidate answers, navigation, proctoring alerts, and submission flow.
"""

import asyncio
import base64
import re
from datetime import datetime
import reflex as rx
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState


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


class CandidateState(rx.State):
    # ── Active Test Session Metadata ─────────────────────────────────────
    active_assessment_name: str = "Quality"
    active_test_name: str = "Test 1"

    # Test Session State
    current_question_index: int = 2  # Question 3 (as shown in screenshot)
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
    auto_save_status: str = "Auto-saved"

    # ── Proctoring Mock State ───────────────────────────────────────────
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

    # ── Computed Variables ──────────────────────────────────────────────
    @rx.var
    def current_question(self) -> dict:
        if 0 <= self.current_question_index < len(MOCK_SUBJECTIVE_QUESTIONS):
            return MOCK_SUBJECTIVE_QUESTIONS[self.current_question_index]
        return MOCK_SUBJECTIVE_QUESTIONS[0]

    @rx.var
    def current_question_number(self) -> int:
        return self.current_question_index + 1

    @rx.var
    def total_questions(self) -> int:
        return len(MOCK_SUBJECTIVE_QUESTIONS)

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
        for q in MOCK_SUBJECTIVE_QUESTIONS:
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

    # ── Timer & Actions ──────────────────────────────────────────────────

    @rx.event(background=True)
    async def run_timer(self):
        """Live countdown timer running every second."""
        current_session = self.timer_session_id
        while True:
            await asyncio.sleep(1)
            async with self:
                if self.timer_session_id != current_session or self.is_test_submitted or self.is_time_expired:
                    break
                if self.total_time_seconds <= 1:
                    self.total_time_seconds = 0
                    self.time_display = "00:00:00"
                    self.is_time_expired = True
                    self.handle_time_expired()
                    break
                self.total_time_seconds -= 1
                h = self.total_time_seconds // 3600
                m = (self.total_time_seconds % 3600) // 60
                s = self.total_time_seconds % 60
                self.time_display = f"{h:02d}:{m:02d}:{s:02d}"

    def on_test_page_load(self):
        """Called when candidate test page loads to ensure timer is active."""
        if not self.is_test_submitted and not self.is_time_expired:
            self.timer_session_id += 1
            return CandidateState.run_timer

    def handle_time_expired(self):
        """Auto-submit the test when timer reaches 00:00:00."""
        now = datetime.now()
        self.is_test_submitted = True
        self.is_time_expired = True
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.submitted_at = now.strftime("%B %d, %Y at %I:%M %p")
        self.submission_receipt = f"SUB-{now.strftime('%Y%m%d')}-{self.active_test_name.replace(' ', '')}-9841"

    def start_test(self, assessment_name: str, test_name: str):
        """Launch the test session and navigate to /candidate/test."""
        self.active_assessment_name = assessment_name
        self.active_test_name = test_name
        self.current_question_index = 2  # Question 3
        self.is_test_submitted = False
        self.is_time_expired = False
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.violation_count = 0
        self.auto_save_status = "Auto-saved"
        self.total_time_seconds = 5400  # 01:30:00
        self.time_display = "01:30:00"
        self.is_fullscreen = True
        self.timer_session_id += 1
        return [rx.redirect("/candidate/test"), CandidateState.run_timer]

    def set_question_index(self, index: int):
        if 0 <= index < len(MOCK_SUBJECTIVE_QUESTIONS):
            self.current_question_index = index

    def next_question(self):
        if self.current_question_index < len(MOCK_SUBJECTIVE_QUESTIONS) - 1:
            self.current_question_index += 1

    def prev_question(self):
        if self.current_question_index > 0:
            self.current_question_index -= 1

    def update_answer(self, text: str):
        if self.is_test_submitted or self.is_time_expired:
            return
        qid_str = str(self.current_question_number)
        new_answers = dict(self.answers)
        new_answers[qid_str] = text
        self.answers = new_answers
        self.auto_save_status = "Auto-saved"

    def set_answer_html(self, html: str):
        """Save the rich-text HTML produced by the answer editor's
        toolbar/typing for the currently active question. Mirrors
        update_answer but stores markup instead of plain text so
        Bold/Italic/Underline/Lists/etc. persist and redisplay correctly."""
        if self.is_test_submitted or self.is_time_expired:
            return
        qid_str = str(self.current_question_number)
        new_answers = dict(self.answers)
        new_answers[qid_str] = html
        self.answers = new_answers
        self.auto_save_status = "Auto-saved"

    def toggle_mark_for_review(self):
        if self.is_test_submitted or self.is_time_expired:
            return
        qid = self.current_question_number
        if qid in self.marked_for_review:
            self.marked_for_review = [q for q in self.marked_for_review if q != qid]
        else:
            self.marked_for_review = self.marked_for_review + [qid]

    # ── Proctoring Mock Actions ─────────────────────────────────────────

    def trigger_proctoring_warning(self):
        """Simulate a tab switch or screen unfocus violation."""
        if not self.is_test_submitted and not self.is_time_expired:
            self.violation_count += 1
            self.violation_warning_msg = (
                f"Warning #{self.violation_count}: Tab switching or window unfocus detected! "
                f"Your assessment session is monitored. Total violations allowed: {self.max_violations}."
            )
            self.show_violation_modal = True

    def dismiss_violation_modal(self):
        self.show_violation_modal = False

    def exit_fullscreen(self):
        self.is_fullscreen = False
        if not self.is_test_submitted and not self.is_time_expired:
            self.violation_count += 1
            self.violation_warning_msg = (
                f"Warning #{self.violation_count}: Fullscreen exit detected! "
                f"You must remain in fullscreen mode during the examination. Total violations allowed: {self.max_violations}."
            )
            self.show_violation_modal = True
        return rx.call_script("if (document.fullscreenElement) { document.exitFullscreen().catch(function(e){console.warn(e);}); }")

    def handle_fullscreen_exited(self):
        """Detected when browser exits fullscreen."""
        if not self.is_test_submitted and not self.is_time_expired:
            if self.is_fullscreen:
                self.is_fullscreen = False
                self.violation_count += 1
                self.violation_warning_msg = (
                    f"Warning #{self.violation_count}: Fullscreen exit detected! "
                    f"You must remain in fullscreen mode during the examination. Total violations allowed: {self.max_violations}."
                )
                self.show_violation_modal = True

    def handle_fullscreen_entered(self):
        """Detected when browser enters fullscreen."""
        self.is_fullscreen = True

    # ── Submission Flow ─────────────────────────────────────────────────

    def open_submit_dialog(self):
        if not self.is_test_submitted and not self.is_time_expired:
            self.show_submit_dialog = True

    def close_submit_dialog(self):
        self.show_submit_dialog = False

    def confirm_submit_test(self):
        """Submit the assessment test session."""
        now = datetime.now()
        self.is_test_submitted = True
        self.show_submit_dialog = False
        self.submitted_at = now.strftime("%B %d, %Y at %I:%M %p")
        self.submission_receipt = f"SUB-{now.strftime('%Y%m%d')}-{self.active_test_name.replace(' ', '')}-9841"
        return rx.toast.success("Assessment submitted successfully!", duration=4000)

    def return_to_dashboard(self):
        """Navigate back to the candidate dashboard."""
        self.is_test_submitted = False
        self.is_time_expired = False
        return rx.redirect("/candidate/dashboard")


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

        return rx.toast.success(f"Profile photo updated: {file.filename}")

    async def save_profile(self):
        """Save candidate profile changes."""
        return rx.toast.success("Profile saved successfully!")