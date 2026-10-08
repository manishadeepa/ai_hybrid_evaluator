"""
Candidate State Ã¢â‚¬â€ manages candidate dashboard and active test environment session.
Includes question loading from Facilitator-uploaded papers, answers, navigation,
proctoring alerts, and submission flow.
"""

import asyncio
import base64
import json
import re
from datetime import datetime
from pathlib import Path
import reflex as rx
import pandas as pd
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.models.models import get_candidate_profile, save_candidate_profile
from backend.services.assessment_service import AssessmentService
from backend.services.response_lifecycle_service import ResponseLifecycleService
from backend.services.feedback_service import FeedbackService


# Ã¢â€â‚¬Ã¢â€â‚¬ Per-session question store Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
            # Ã¢â€â‚¬Ã¢â€â‚¬ Structured Objective (separate option columns) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
            # Ã¢â€â‚¬Ã¢â€â‚¬ Inline Objective (A) B) C) D) embedded in Question text) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
            # Ã¢â€â‚¬Ã¢â€â‚¬ Subjective Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
    question yet' checks Ã¢â‚¬â€ never for grading or storage."""
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



def _load_dashboard_statuses(cand_id):
    from backend.repositories.json_repository import repository_read_scope
    with repository_read_scope():
        subs: dict[str, dict[str, str]] = {}
        dqs: dict[str, dict[str, str]] = {}

        # Read the candidate's persisted assessments/tests.
        try:
            assessments = AssessmentService().load_assessments()
        except (ValueError, OSError):
            assessments = []

        for assessment in assessments:
            if cand_id not in assessment.get("assigned_candidates", []):
                continue

            assessment_id = assessment.get("assessment_id", "")
            assessment_name = assessment.get("name", "")

            if not assessment_id or not assessment_name:
                continue

            test_ids = assessment.get("test_ids", {})

            if not isinstance(test_ids, dict):
                continue

            for test_name, test_id in test_ids.items():
                if not test_id:
                    continue

                try:
                    lifecycle_record = ResponseLifecycleService().get_response(
                        cand_id,
                        assessment_id,
                        test_id,
                    )
                except (ValueError, OSError):
                    lifecycle_record = None

                if not lifecycle_record:
                    continue

                status = lifecycle_record.get("status", "")

                if status == "Submitted":
                    if assessment_name not in subs:
                        subs[assessment_name] = {}

                    subs[assessment_name][test_name] = (
                        lifecycle_record.get("submitted_at", "") or ""
                    )

                elif status == "Disqualified":
                    if assessment_name not in dqs:
                        dqs[assessment_name] = {}

                    dqs[assessment_name][test_name] = (
                        lifecycle_record.get("terminated_at")
                        or lifecycle_record.get("submitted_at")
                        or ""
                    )

        return subs, dqs


class CandidateState(rx.State):
    # Candidate identity (emp_id or email)
    candidate_id: str = "CAND-2031"

    # Ã¢â€â‚¬Ã¢â€â‚¬ Active Test Session Metadata Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    active_assessment_name: str = "Quality"
    active_test_name: str = "Formative 1"
    active_assessment_id: str = ""
    active_test_id: str = ""

    # Test Session State
    questions: list[dict] = []  # Candidate-safe canonical snapshot tracked by Reflex.
    current_question_index: int = 0  # Always start at Question 1
    total_time_seconds: int = 5400  # 01:30:00 (90 minutes)
    time_display: str = "01:30:00"
    is_time_expired: bool = False
    is_submitting: bool = False
    timer_session_id: int = 0

    # Candidate Answers Ã¢â‚¬â€ dictionary mapping question ID (str) to answer
    # HTML (rich-text content from the answer editor) for Subjective questions.
    answers: dict[str, str] = {}

    # MCQ Answers Ã¢â‚¬â€ dictionary mapping question ID (str) to selected option letter
    # e.g. {"1": "A", "3": "C"}  for Objective questions.
    mcq_answers: dict[str, str] = {}

    # Marked for Review question IDs (list of ints)
    marked_for_review: list[int] = []

    # Auto-save indicator text
    auto_save_status: str = ""

    # Ã¢â€â‚¬Ã¢â€â‚¬ Question Navigation Panel State Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    nav_filter: str = "all"  # "all" | "objective" | "subjective"
    show_instructions: bool = True

    # Ã¢â€â‚¬Ã¢â€â‚¬ Test completion stores for dashboard reactivity Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    # Structure: { assessment_name: { test_name: timestamp } }
    # Mirrors FacilitatorState.question_papers for seamless .contains() checks in Reflex
    submitted_tests: dict[str, dict[str, str]] = {}
    disqualified_tests: dict[str, dict[str, str]] = {}

    # Ã¢â€â‚¬Ã¢â€â‚¬ Proctoring State Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    is_fullscreen: bool = False
    is_tab_locked: bool = True
    camera_active: bool = True
    mic_active: bool = True
    violation_count: int = 0
    max_violations: int = 3
    show_violation_modal: bool = False
    violation_warning_msg: str = ""

    # Ã¢â€â‚¬Ã¢â€â‚¬ Submission State Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    show_submit_dialog: bool = False
    is_test_submitted: bool = False
    submission_receipt: str = ""
    submitted_at: str = ""

    # Ã¢â€â‚¬Ã¢â€â‚¬ Score snapshot (populated on dashboard load from FacilitatorState) Ã¢â€â‚¬Ã¢â€â‚¬
    # Flat dicts with composite keys to work cleanly inside rx.foreach vars.
    # Key for test-level: "AssessmentName::TestName"
    candidate_test_scores: dict[str, str] = {}      # -> score_str e.g. "72%" or "-"
    candidate_test_evaluated: dict[str, bool] = {}  # -> True / False

    # Ã¢â€â‚¬Ã¢â€â‚¬ Candidate Feedback State (Post-submission) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    show_candidate_feedback_modal: bool = False
    candidate_feedback_questions: list[dict] = []
    candidate_feedback_answers: dict[str, str] = {}
    candidate_feedback_error: str = ""
    saved_candidate_feedbacks: dict[str, dict] = {}

    # Ã¢â€â‚¬Ã¢â€â‚¬ Candidate Identity Helper Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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

    def _get_current_original_qid_str(self) -> str:
        """The canonical session snapshot already owns the shuffled order."""
        return str(self.current_question_number)

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

    @rx.var
    def current_question(self) -> dict:
        qs = self.questions
        if not qs:
            return {}
        idx = self.current_question_index
        if 0 <= idx < len(qs):
            return qs[idx]
        return qs[0]

    @rx.var
    def current_question_number(self) -> int:
        """Stable original question ID used for saving and evaluation."""
        questions = self.questions
        if 0 <= self.current_question_index < len(questions):
            return questions[self.current_question_index]["id"]
        return self.current_question_index + 1

    @rx.var
    def current_question_display_number(self) -> int:
        """Sequential 1-based number shown to the candidate after shuffling."""
        return self.current_question_index + 1

    @rx.var
    def total_questions(self) -> int:
        return len(self.questions)

    @rx.var
    def current_original_question_id(self) -> str:
        """UI alias for the original ID in the persisted shuffled snapshot."""
        return str(self.current_question_number)

    @rx.var
    def current_answer_text(self) -> str:
        # Key by ORIGINAL question id (survives shuffle)
        qid_str = self.current_original_question_id
        return self.answers.get(qid_str, "")

    @rx.var
    def current_word_count(self) -> int:
        text = _strip_html(self.current_answer_text)
        if not text:
            return 0
        return len(text.split())

    @rx.var
    def is_current_marked(self) -> bool:
        # marked_for_review stores original question ids
        try:
            orig_id = int(self.current_original_question_id)
        except (ValueError, TypeError):
            orig_id = self.current_question_number
        return (orig_id in self.marked_for_review) or (self.current_original_question_id in self.marked_for_review)

    @rx.var
    def answered_count(self) -> int:
        # Iterate original questions (answers are keyed by original id)
        count = 0
        for q in self.questions:
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

    # current_question_type is defined after nav_questions to use current_question var

    @rx.var
    def current_mcq_answer(self) -> str:
        """Returns the selected option letter (e.g. 'A') for the current MCQ question.
        Keyed by ORIGINAL question id."""
        qid_str = self.current_original_question_id
        return self.mcq_answers.get(qid_str, "")

    @rx.var
    def current_option_a(self) -> str:
        q = self.current_question
        return str(q.get("options", {}).get("A", "")) if q else ""

    @rx.var
    def current_option_b(self) -> str:
        q = self.current_question
        return str(q.get("options", {}).get("B", "")) if q else ""

    @rx.var
    def current_option_c(self) -> str:
        q = self.current_question
        return str(q.get("options", {}).get("C", "")) if q else ""

    @rx.var
    def current_option_d(self) -> str:
        q = self.current_question
        return str(q.get("options", {}).get("D", "")) if q else ""

    @rx.var
    def current_mcq_selected_display(self) -> str:
        """Returns formatted string like 'A. Quality Function Deployment (QFD)' for selected option."""
        letter = self.current_mcq_answer
        if not letter:
            return ""
        q = self.current_question
        raw_text = str(q.get("options", {}).get(letter, "")) if q else ""
        raw_text = raw_text.strip()
        clean_text = re.sub(r"^[A-Za-z][\.\)]\s*", "", raw_text)
        return f"{letter}.  {clean_text}" if clean_text else (f"{letter}.  {raw_text}" if raw_text else letter)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Question Navigation Computed Vars Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @rx.var
    def nav_questions(self) -> list[dict]:
        """All uploaded questions for the navigation panel Ã¢â‚¬â€ no type filtering."""
        items = []
        curr = self.current_question_number
        marked_set = set(self.marked_for_review)

        for position, q in enumerate(self.questions, 1):
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
                "id": position,
                "orig_id": q_id,
                "number": str(position),
                "position": position,
                "type": q_type,
                "status": status,
                "is_current": is_curr,
                "is_marked": is_marked,
                "is_answered": is_answered,
            })
        return items

    @rx.var
    def total_nav_count(self) -> int:
        return len(self.questions)

    @rx.var
    def objective_nav_count(self) -> int:
        return sum(1 for q in self.questions if q.get("question_type") == "Objective")

    @rx.var
    def subjective_nav_count(self) -> int:
        return sum(1 for q in self.questions if q.get("question_type") == "Subjective")

    @rx.var
    def current_question_type(self) -> str:
        """Returns 'Objective' or 'Subjective' for the currently displayed (shuffled) question."""
        q = self.current_question
        return str(q.get("question_type", "Subjective")) if q else "Subjective"

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
        return self.current_question_index >= len(self.questions) - 1

    # Ã¢â€â‚¬Ã¢â€â‚¬ Question metadata computed vars (CO / LO / RBT / Marks) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    # Access self.questions directly (cannot chain .get() on an rx.var result)




    # ── Question metadata computed vars (CO / LO / RBT / Marks) ───────────────
    @rx.var
    def current_question_marks(self) -> str:
        q = self.current_question
        v = q.get("marks", "") if q else ""
        return str(v) if v != "" else ""

    @rx.var
    def current_question_co(self) -> str:
        q = self.current_question
        return str(q.get("co", "")) if q else ""

    @rx.var
    def current_question_lo(self) -> str:
        q = self.current_question
        return str(q.get("lo", "")) if q else ""

    @rx.var
    def current_question_rbt(self) -> str:
        q = self.current_question
        return str(q.get("rbt_level", "")) if q else ""

    # Ã¢â€â‚¬Ã¢â€â‚¬ Timer & Actions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

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
        """
        Called when the candidate dashboard loads.

        The canonical backend is the source of truth for Submitted and
        Disqualified test status. The in-memory cache is used only as a
        compatibility fallback.
        """
        cand_id = await self._get_current_candidate_id()

        subs, dqs = await asyncio.to_thread(_load_dashboard_statuses, cand_id)

        # Compatibility fallback for legacy/in-memory records.
        # Canonical backend status always takes priority.
        for rec in PERSISTED_CANDIDATE_TEST_DATA.values():
            if rec.get("candidate_id") != cand_id:
                continue

            assessment_name = rec.get("assessment_name", "")
            test_name = rec.get("test_name", "")
            status = rec.get("status", "")

            if not assessment_name or not test_name:
                continue

            already_canonical = (
                test_name in subs.get(assessment_name, {})
                or test_name in dqs.get(assessment_name, {})
            )

            if already_canonical:
                continue

            if status == "Submitted":
                if assessment_name not in subs:
                    subs[assessment_name] = {}

                subs[assessment_name][test_name] = (
                    rec.get("submitted_at", "") or ""
                )

            elif status == "Disqualified":
                if assessment_name not in dqs:
                    dqs[assessment_name] = {}

                dqs[assessment_name][test_name] = (
                    rec.get("submitted_at", "") or ""
                )

        # Update dashboard-reactive state.
        self.submitted_tests = subs
        self.disqualified_tests = dqs

        # Refresh evaluation/score information.
        await self.refresh_candidate_scores()
    async def refresh_candidate_scores(self):
        """Read evaluation results + weightages from FacilitatorState and build
        a per-assessment score snapshot for the currently logged-in candidate.
        Only reads data Ã¢â‚¬â€ never writes to any submission or proctoring store."""
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
        """
        Restore the active candidate test from the canonical persisted
        response lifecycle.

        This makes the test page recover correctly after a page refresh,
        temporary websocket disconnect, or Reflex state recreation.
        """
        cand_id = await self._get_current_candidate_id()
        self.candidate_id = cand_id

        lifecycle = ResponseLifecycleService()
        selected = None

        # ------------------------------------------------------------
        # 1. If the current Reflex state still contains canonical IDs,
        #    restore that exact session first.
        # ------------------------------------------------------------
        if self.active_assessment_id and self.active_test_id:
            try:
                record = await asyncio.to_thread(
                    lifecycle.get_response,
                    cand_id,
                    self.active_assessment_id,
                    self.active_test_id,
                )
            except (ValueError, OSError):
                record = None

            if record:
                selected = (
                    self.active_assessment_name,
                    self.active_test_name,
                    self.active_assessment_id,
                    self.active_test_id,
                    record,
                )

        # ------------------------------------------------------------
        # 2. If Reflex state was lost, recover the candidate's latest
        #    persisted In Progress test from the canonical backend.
        # ------------------------------------------------------------
        if selected is None:
            try:
                assessments = await asyncio.to_thread(AssessmentService().load_assessments)
            except (ValueError, OSError):
                assessments = []

            active_sessions = []

            for assessment in assessments:
                if cand_id not in assessment.get("assigned_candidates", []):
                    continue

                assessment_id = assessment.get("assessment_id", "")
                assessment_name = assessment.get("name", "")

                if not assessment_id or not assessment_name:
                    continue

                test_ids = assessment.get("test_ids", {})

                if not isinstance(test_ids, dict):
                    continue

                for test_name, test_id in test_ids.items():
                    if not test_id:
                        continue

                    try:
                        record = await asyncio.to_thread(
                            lifecycle.get_response,
                            cand_id,
                            assessment_id,
                            test_id,
                        )
                    except (ValueError, OSError):
                        continue

                    if record and record.get("status") == "In Progress":
                        active_sessions.append(
                            (
                                assessment_name,
                                test_name,
                                assessment_id,
                                test_id,
                                record,
                            )
                        )

            if active_sessions:
                # If more than one old In Progress session exists, recover
                # the most recently started one.
                selected = max(
                    active_sessions,
                    key=lambda item: (
                        item[4].get("started_at")
                        or item[4].get("created_at")
                        or item[4].get("updated_at")
                        or ""
                    ),
                )

        # ------------------------------------------------------------
        # 3. No persisted active test exists.
        # ------------------------------------------------------------
        if selected is None:
            self.show_submit_dialog = False
            self.show_violation_modal = False

            return [
                rx.toast.error(
                    "No active test session could be restored. "
                    "Please start the test again from My Assessments."
                ),
                rx.redirect("/candidate/dashboard"),
            ]

        (
            assessment_name,
            test_name,
            assessment_id,
            test_id,
            lifecycle_record,
        ) = selected

        # ------------------------------------------------------------
        # 4. Restore canonical identity.
        # ------------------------------------------------------------
        self.active_assessment_name = assessment_name
        self.active_test_name = test_name
        self.active_assessment_id = assessment_id
        self.active_test_id = test_id

        # ------------------------------------------------------------
        # 5. Restore the canonical question snapshot.
        # ------------------------------------------------------------
        questions = lifecycle_record.get("questions", [])

        self.questions = [
            dict(
                question,
                text=question.get(
                    "question_stem",
                    question.get("text", ""),
                ),
            )
            for question in questions
        ]

        # ------------------------------------------------------------
        # 6. Restore lifecycle status.
        # ------------------------------------------------------------
        status = lifecycle_record.get("status", "")

        if status == "Submitted":
            self.is_test_submitted = True
            self.submitted_at = lifecycle_record.get("submitted_at", "") or ""
            self.submission_receipt = (
                lifecycle_record.get("submission_receipt", "") or ""
            )
            self.show_submit_dialog = False
            self.show_violation_modal = False

            return rx.redirect("/candidate/dashboard")

        if status == "Disqualified":
            self.is_test_submitted = True
            self.violation_count = self.max_violations
            self.submitted_at = (
                lifecycle_record.get("terminated_at")
                or lifecycle_record.get("submitted_at")
                or ""
            )
            self.submission_receipt = (
                lifecycle_record.get("submission_receipt", "") or ""
            )
            self.show_submit_dialog = False
            self.show_violation_modal = False

            return rx.redirect("/candidate/dashboard")

        # ------------------------------------------------------------
        # 7. Restore an In Progress test.
        # ------------------------------------------------------------
        self.is_test_submitted = False
        self.is_time_expired = False
        self.show_submit_dialog = False
        self.show_violation_modal = False
        self.auto_save_status = "Auto-saved"

        objective_ids = {
            str(question["id"])
            for question in self.questions
            if question.get("question_type") == "Objective"
        }

        saved_answers = dict(lifecycle_record.get("answers", {}))

        self.answers = {
            key: value
            for key, value in saved_answers.items()
            if key not in objective_ids
        }

        self.mcq_answers = {
            key: value
            for key, value in saved_answers.items()
            if key in objective_ids
        }

        self.marked_for_review = list(
            lifecycle_record.get("marked_for_review", [])
        )

        self.violation_count = min(
            lifecycle_record.get("violation_count", 0),
            self.max_violations,
        )

        # Preserve the candidate's current question when Reflex merely
        # reloads/reconnects the active test page. Only fall back to Q1 when
        # the existing index is no longer valid for the recovered snapshot.
        if not (
            0 <= self.current_question_index < len(self.questions)
        ):
            self.current_question_index = 0

        # Keep the legacy UI cache synchronized.
        self._save_current_test_record(status="In Progress")

        # Restart only the currently valid timer session.
        self.timer_session_id += 1

        events = [CandidateState.run_timer]

        restore = self._restore_rte_script()
        if restore is not None:
            events.append(restore)

        return events

    async def handle_time_expired(self):
        """Auto-submit the test through the canonical lifecycle when time expires."""
        if self.is_test_submitted:
            return

        if not self.active_assessment_id or not self.active_test_id:
            return rx.toast.error(
                "Unable to auto-submit because the active test identity is missing."
            )

        cand_id = self.candidate_id or "CAND-2031"

        # Combine subjective/rich-text and MCQ answers.
        final_answers = dict(self.answers)
        final_answers.update(self.mcq_answers)

        try:
            lifecycle_record = await asyncio.to_thread(ResponseLifecycleService().handle_time_expired,
                cand_id,
                self.active_assessment_id,
                self.active_test_id,
                answers=final_answers,
            )
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

        # Update UI only after canonical submission succeeds.
        self.is_test_submitted = True
        self.is_time_expired = True
        self.show_submit_dialog = False
        self.show_violation_modal = False

        self.submitted_at = lifecycle_record.get("submitted_at", "") or ""
        self.submission_receipt = lifecycle_record.get(
            "submission_receipt",
            "",
        )

        subs = {k: dict(v) for k, v in self.submitted_tests.items()}
        if self.active_assessment_name not in subs:
            subs[self.active_assessment_name] = {}

        subs[self.active_assessment_name][
            self.active_test_name
        ] = self.submitted_at

        self.submitted_tests = subs
        self._save_current_test_record(status="Submitted")

    async def start_test(self, assessment_name: str, test_name: str):
        """Launch the test session and navigate to /candidate/test. Blocks already submitted tests."""
        cand_id = await self._get_current_candidate_id()

        # Resolve the UI assessment/test names to their canonical persisted IDs.
        assessment = next(
            (
                item
                for item in await asyncio.to_thread(AssessmentService().load_assessments)
                if item.get("name") == assessment_name
                and cand_id in item.get("assigned_candidates", [])
            ),
            None,
        )

        if not assessment:
            return rx.toast.error("This assessment is not assigned to this candidate.")

        assessment_id = assessment.get("assessment_id", "")
        test_id = assessment.get("test_ids", {}).get(test_name, "")

        if not assessment_id or not test_id:
            return rx.toast.error("Unable to resolve this test in the persisted assessment.")

        # Start or recover the canonical backend response session.
        try:
            lifecycle_record = await asyncio.to_thread(ResponseLifecycleService().start_test,
                cand_id,
                assessment_id,
                test_id,
            )
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

        key = f"{cand_id}::{assessment_name}::{test_name}"
        record = PERSISTED_CANDIDATE_TEST_DATA.get(key)

        if record:
            if record.get("status") == "Submitted":
                return rx.toast.info("This test has already been submitted and cannot be retaken.")
            if record.get("status") == "Disqualified":
                return rx.toast.error("This test was terminated due to proctoring violations and cannot be retaken.")

        self.active_assessment_name = assessment_name
        self.active_test_name = test_name
        self.active_assessment_id = assessment_id
        self.active_test_id = test_id

        # Use the canonical response snapshot; it contains options, never answer keys.
        self.questions = [dict(q, text=q.get("question_stem", q["text"]))
                                        for q in lifecycle_record["questions"]]

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
        self.is_fullscreen = False

        self.violation_count = min(lifecycle_record.get("violation_count", 0), self.max_violations)
        objective_ids = {str(q["id"]) for q in lifecycle_record["questions"] if q.get("question_type") == "Objective"}
        self.answers = {k: v for k, v in lifecycle_record["answers"].items() if k not in objective_ids}
        self.mcq_answers = {k: v for k, v in lifecycle_record["answers"].items() if k in objective_ids}
        self.marked_for_review = list(lifecycle_record.get("marked_for_review", []))
        self._save_current_test_record(status="In Progress")

        return [rx.call_script("if (!document.fullscreenElement) { document.documentElement.requestFullscreen().catch(function(){}); }"),
                rx.redirect("/candidate/test")]


    def _restore_rte_script(self):
        """Return a call_script that pushes the currently saved answer HTML
        into the contenteditable editor AND sets the data-* attributes on the
        relay input so the localStorage helpers know the current
        candidate/assessment/test/question context.
        Called after every question-navigation action."""
        if self.current_question_type == "Objective":
            return None
        qid_str = self._get_current_original_qid_str()
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
        """Navigate immediately to an already-loaded question.

        The browser flushes the outgoing editor answer before grid navigation,
        so navigation itself must stay lightweight and must not rewrite the
        complete persisted candidate-test snapshot.
        """
        if 0 <= index < len(self.questions):
            self.current_question_index = index
            return self._restore_rte_script()

    def jump_to_question(self, q_num: int):
        """Immediately open the specified question number (1-based index)."""
        return self.set_question_index(q_num - 1)

    def set_nav_filter(self, f: str):
        self.nav_filter = f

    def toggle_instructions(self):
        self.show_instructions = not self.show_instructions

    def next_question(self):
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            return self._restore_rte_script()

    def prev_question(self):
        if self.current_question_index > 0:
            self.current_question_index -= 1
            return self._restore_rte_script()

    async def update_answer(self, text: str):
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        question_id = self.current_question_number
        qid_str = str(question_id)
        new_answers = dict(self.answers)
        new_answers[qid_str] = text
        self.answers = new_answers
        self.auto_save_status = "Saving..."
        self._save_current_test_record()

        # Persist the answer in the canonical response lifecycle backend.
        yield

        if self.active_assessment_id and self.active_test_id:
            try:
                await asyncio.to_thread(ResponseLifecycleService().save_answer,
                    self.candidate_id or "CAND-2031",
                    self.active_assessment_id,
                    self.active_test_id,
                    question_id,
                    text,
                )
                self.auto_save_status = "Auto-saved"
            except (ValueError, OSError):
                self.auto_save_status = "Save failed"

    async def select_mcq_option(self, option: str):
        """Select an MCQ immediately and persist it using the stable question ID."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        # Use the ORIGINAL question ID because displayed questions are shuffled.
        question_id = self.current_question_number
        qid_str = str(question_id)

        if option not in ("A", "B", "C", "D"):
            return

        if (
            self.mcq_answers.get(qid_str) == option
            and self.auto_save_status == "Auto-saved"
        ):
            return
        new_mcq = dict(self.mcq_answers)
        new_mcq[qid_str] = option
        self.mcq_answers = new_mcq

        self.auto_save_status = "Saving..."

        # Release state immediately so the UI reflects the selected option.
        yield

        # Persist the local snapshot after the UI has updated.
        self._save_current_test_record()

        if self.active_assessment_id and self.active_test_id:
            try:
                await asyncio.to_thread(
                    ResponseLifecycleService().save_answer,
                    self.candidate_id or "CAND-2031",
                    self.active_assessment_id,
                    self.active_test_id,
                    question_id,
                    option,
                )
                self.auto_save_status = "Auto-saved"
            except (ValueError, OSError):
                self.auto_save_status = "Save failed"

    async def clear_mcq_answer(self):
        """Clear the MCQ answer for the current Objective question."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        # Use original question ID because displayed questions are shuffled.
        question_id = self.current_question_number
        qid_str = str(question_id)
        new_mcq = dict(self.mcq_answers)
        new_mcq.pop(qid_str, None)
        self.mcq_answers = new_mcq
        self.auto_save_status = "Saving..."

        # Update the UI immediately.
        yield

        # Persist the local snapshot after the UI has updated.
        self._save_current_test_record()

        # Clear the MCQ answer from the canonical response backend too.

        if self.active_assessment_id and self.active_test_id:
            try:
                await asyncio.to_thread(ResponseLifecycleService().save_answer,
                    self.candidate_id or "CAND-2031",
                    self.active_assessment_id,
                    self.active_test_id,
                    question_id,
                    "",
                    clear=True,
                )
                self.auto_save_status = "Auto-saved"
            except (ValueError, OSError):
                self.auto_save_status = "Save failed"

    async def set_answer_payload(self, payload: str):
        """The editor carries its question ID so a late relay cannot target the next question."""
        try:
            value = json.loads(payload)
            qid = int(value["question_id"])
            html = value["html"]
            if not isinstance(html, str) or qid not in {q["id"] for q in self.questions}:
                return
        except (ValueError, TypeError, KeyError):
            return
        async for event in self.set_answer_html(html, qid):
            yield event

    async def set_answer_html(self, html: str, question_id: int = 0):
        """Save the rich-text HTML produced by the answer editor's toolbar/typing
        for the currently active question.
        Guard: never overwrite a non-empty saved answer with an empty value
        (prevents navigation/rerender clearing existing answers)."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        # Prefer the question ID captured by the editor event.
        # This prevents a delayed editor update from being saved to
        # a different question after the candidate navigates.
        qid_str = (
            str(question_id)
            if question_id
            else self._get_current_original_qid_str()
        )
        # Guard: do not overwrite a non-empty saved answer with empty HTML
        existing = self.answers.get(qid_str, "")
        if html == existing and self.auto_save_status == "Auto-saved":
            return
        if not html.strip() and _strip_html(existing).strip():
            return
        self.auto_save_status = "Saving..."
        try:
            new_answers = dict(self.answers)
            new_answers[qid_str] = html
            self.answers = new_answers

            # Update the browser immediately before persistence work.
            yield

            # Preserve the local compatibility snapshot after the UI update.
            self._save_current_test_record()

            # Persist rich-text answer in the canonical response backend.
            if self.active_assessment_id and self.active_test_id:
                await asyncio.to_thread(ResponseLifecycleService().save_answer,
                    self.candidate_id or "CAND-2031",
                    self.active_assessment_id,
                    self.active_test_id,
                    int(qid_str),
                    html,
                )

            self.auto_save_status = "Auto-saved"
        except (ValueError, OSError):
            self.auto_save_status = "Save failed"

    async def toggle_mark_for_review(self):
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        orig_str = self._get_current_original_qid_str()
        try:
            qid = int(orig_str)
        except (ValueError, TypeError):
            qid = self.current_question_number
        current_list = list(self.marked_for_review)
        if qid in current_list or orig_str in current_list:
            # Unmark: remove this question
            self.marked_for_review = [q for q in current_list if q != qid and q != orig_str]
        else:
            # Mark: add only if not already present
            if qid not in current_list:
                self.marked_for_review = current_list + [qid]
        self.auto_save_status = "Saving..."

        # Update the review marker immediately.
        yield

        # Persist the local snapshot after the UI has updated.
        self._save_current_test_record()

        # Persist review status in the canonical response backend.

        if self.active_assessment_id and self.active_test_id:
            try:
                await asyncio.to_thread(ResponseLifecycleService().mark_for_review,
                    self.candidate_id or "CAND-2031",
                    self.active_assessment_id,
                    self.active_test_id,
                    qid,
                    qid in self.marked_for_review,
                )
                self.auto_save_status = "Auto-saved"
            except (ValueError, OSError):
                self.auto_save_status = "Save failed"

    def save_and_next_question(self):
        """Advance immediately after the outgoing answer has been captured.

        The answer is already updated/persisted through set_answer_html(),
        so navigation must not perform another synchronous snapshot write.
        """
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            return self._restore_rte_script()

    async def _navigate_with_answer(self, payload: str, action: str):
        """Capture the outgoing editor before moving; persist its stable question ID."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        save = None
        if payload:
            try:
                value = json.loads(payload)
                qid = int(value["question_id"])
                html = value["html"]
                if qid != self.current_question_number or not isinstance(html, str):
                    return
            except (ValueError, TypeError, KeyError):
                return
            save = self.set_answer_html(html, qid)
            try:
                await anext(save)
            except StopAsyncIteration:
                save = None
        if action == "previous":
            event = self.prev_question()
        else:
            event = self.save_and_next_question()
        # Send navigation before waiting for the outgoing answer's disk write.
        yield event
        if save is not None:
            async for event in save:
                yield event
        if action == "submit":
            yield self.open_submit_dialog()

    async def next_with_answer(self, payload: str):
        async for event in self._navigate_with_answer(payload, "next"):
            yield event

    async def previous_with_answer(self, payload: str):
        async for event in self._navigate_with_answer(payload, "previous"):
            yield event

    async def submit_with_answer(self, payload: str):
        async for event in self._navigate_with_answer(payload, "submit"):
            yield event

    async def _record_violation(self, reason: str):
        """Publish one warning per acknowledged incident, including overlapping signals."""
        if self.show_violation_modal or self.is_disqualified or self.is_test_submitted:
            return
        self.violation_count = min(self.violation_count + 1, self.max_violations)
        self.violation_warning_msg = (
            f"Warning {self.violation_count} of {self.max_violations}: {reason} "
            "Your assessment session is monitored."
        )
        self.show_violation_modal = True
        self._save_current_test_record()
        yield
        if self.active_assessment_id and self.active_test_id:
            try:
                record = await asyncio.to_thread(ResponseLifecycleService().update_violation_count,
                    self.candidate_id or "CAND-2031", self.active_assessment_id,
                    self.active_test_id, self.violation_count)
                self.violation_count = record.get("violation_count", self.violation_count)
                if self.violation_count >= self.max_violations:
                    event = self._terminate_for_violations(record)
                    if event is not None:
                        yield event
            except (ValueError, OSError) as exc:
                yield rx.toast.error(f"Unable to persist proctoring violation: {exc}")

    async def trigger_proctoring_warning(self):
        """Record one browser-reported away episode."""
        if self.is_test_submitted or self.is_time_expired or self.is_disqualified:
            return
        async for event in self._record_violation("Tab switching or window unfocus detected!"):
            yield event

    def dismiss_violation_modal(self):
        if not self.is_disqualified:
            self.show_violation_modal = False

    def exit_fullscreen(self):
        # Only fullscreenchange confirms an exit and records the violation.
        return rx.call_script("if (document.fullscreenElement) { document.exitFullscreen().catch(console.warn); }")

    async def handle_fullscreen_exited(self):
        was_fullscreen = self.is_fullscreen
        self.is_fullscreen = False
        if was_fullscreen and not self.is_test_submitted and not self.is_time_expired and not self.is_disqualified:
            async for event in self._record_violation(
                "Fullscreen exit detected! You must remain in fullscreen mode during the examination."):
                yield event

    def _terminate_for_violations(self, lifecycle_record: dict | None = None):
        """Reflect the canonical backend disqualification in the candidate UI."""
        self.violation_count = self.max_violations

        if not self.active_assessment_id or not self.active_test_id:
            return rx.toast.error(
                "Unable to terminate because the active test identity is missing."
            )

        cand_id = self.candidate_id or "CAND-2031"

        if lifecycle_record is None:
            try:
                lifecycle_record = ResponseLifecycleService().get_response(
                    cand_id,
                    self.active_assessment_id,
                    self.active_test_id,
                )
            except (ValueError, OSError) as exc:
                return rx.toast.error(str(exc))

        if not lifecycle_record or lifecycle_record.get("status") != "Disqualified":
            return rx.toast.error(
                "The backend has not recorded this test as disqualified."
            )

        # Copy canonical backend disqualification metadata into UI state.
        self.submitted_at = (
            lifecycle_record.get("terminated_at")
            or lifecycle_record.get("submitted_at")
            or ""
        )
        self.submission_receipt = lifecycle_record.get(
            "submission_receipt",
            "",
        )

        # Keep the legacy/UI disqualified-tests map synchronized.
        dqs = {k: dict(v) for k, v in self.disqualified_tests.items()}
        if self.active_assessment_name not in dqs:
            dqs[self.active_assessment_name] = {}

        dqs[self.active_assessment_name][
            self.active_test_name
        ] = self.submitted_at

        self.disqualified_tests = dqs

        self.is_test_submitted = True
        self.show_violation_modal = True
        self.show_submit_dialog = False

        self.violation_warning_msg = (
            f"Warning {self.max_violations} of {self.max_violations}: "
            f"You have reached the maximum allowed proctoring violations "
            f"({self.max_violations} of {self.max_violations}). "
            "Your test has been terminated and flagged as Disqualified."
        )

        # Keep the legacy UI/session cache synchronized with canonical state.
        self._save_current_test_record(status="Disqualified")

    async def sync_fullscreen(self, active: bool):
        """Synchronize on each mount, including client-side route revisits."""
        if active:
            self.handle_fullscreen_entered()
        else:
            async for event in self.handle_fullscreen_exited():
                yield event

    def handle_fullscreen_entered(self):
        """Detected when browser enters fullscreen."""
        self.is_fullscreen = True

    # Ã¢â€â‚¬Ã¢â€â‚¬ Submission Flow Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def open_submit_dialog(self):
        if not self.is_test_submitted and not self.is_time_expired and not self.is_disqualified:
            self.show_submit_dialog = True

    def close_submit_dialog(self):
        self.show_submit_dialog = False

    async def confirm_submit_test(self, editor_payload: str = ""):
        """Submit the assessment through the canonical response lifecycle."""
        if self.is_test_submitted or self.is_submitting:
            return
        if not self.active_assessment_id or not self.active_test_id:
            yield rx.toast.error("Unable to submit because the active test identity is missing.")
            return

        auth = await self.get_state(AuthState)

        if not auth.is_candidate_authenticated or not auth.candidate_emp_id:
            yield rx.toast.error("Your session has expired. Please sign in again.")
            return

        cand_id = auth.candidate_emp_id

        if self.candidate_id != cand_id:
            yield rx.toast.error(
                "This test session does not belong to the signed-in candidate. "
                "Please reopen your test from the dashboard."
            )
            return
        # Best-effort capture of the currently visible subjective editor.
        #
        # A stale/missing editor relay must NEVER block final submission.
        # Previously, an invalid editor payload returned early here and prevented
        # ResponseLifecycleService.submit() from running at all.
        if editor_payload:
            try:
                payload = json.loads(editor_payload)
                qid = int(payload.get("question_id"))
                html = payload.get("html")

                is_subjective_question = any(
                    q.get("id") == qid
                    and q.get("question_type") != "Objective"
                    for q in self.questions
                )

                if isinstance(html, str) and is_subjective_question:
                    if (
                        html.strip()
                        or not _strip_html(
                            self.answers.get(str(qid), "")
                        ).strip()
                    ):
                        self.answers = {
                            **self.answers,
                            str(qid): html,
                        }
                else:
                    print(
                        "SUBMIT: ignoring stale/irrelevant editor payload",
                        {
                            "question_id": qid,
                            "is_subjective": is_subjective_question,
                        },
                        flush=True,
                    )

            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                # Existing autosaved answers remain authoritative.
                # Do not abort the entire assessment submission because the
                # browser editor relay is stale or unavailable.
                print(
                    "SUBMIT: editor payload ignored:",
                    type(exc).__name__,
                    str(exc),
                    flush=True,
                )
        # Combine subjective/rich-text and MCQ answers.
        final_answers = dict(self.answers)
        final_answers.update(self.mcq_answers)

        self.is_submitting = True
        yield
        try:
            lifecycle_record = await asyncio.to_thread(ResponseLifecycleService().submit,
                cand_id,
                self.active_assessment_id,
                self.active_test_id,
                answers=final_answers,
            )
        except Exception as exc:
            # Never leave the candidate UI permanently stuck in
            # "Submitting..." when persistence raises an unexpected error.
            self.is_submitting = False
            print(
                "CANDIDATE SUBMIT FAILED:",
                type(exc).__name__,
                str(exc),
                flush=True,
            )
            yield rx.toast.error(
                f"Submission failed: {type(exc).__name__}: {exc}",
                duration=10000,
            )
            return

        # Only mark the UI submitted after canonical persistence succeeds.
        self.is_submitting = False
        self.is_test_submitted = True
        self.show_submit_dialog = False
        self.show_violation_modal = False

        self.submitted_at = lifecycle_record.get("submitted_at", "") or ""
        self.submission_receipt = lifecycle_record.get(
            "submission_receipt",
            "",
        )

        subs = {k: dict(v) for k, v in self.submitted_tests.items()}
        if self.active_assessment_name not in subs:
            subs[self.active_assessment_name] = {}

        subs[self.active_assessment_name][
            self.active_test_name
        ] = self.submitted_at

        self.submitted_tests = subs

        self._save_current_test_record(status="Submitted")

        # After every successful test submission, retrieve the
        # Admin-created Candidate Feedback Form for this assessment.
        try:
            feedback_service = FeedbackService()
            form = await asyncio.to_thread(feedback_service.pending_form,
                "candidate",
                cand_id,
                self.active_assessment_id,
                self.active_test_id,
            )

            if form:
                self.candidate_feedback_questions = list(
                    form.get("questions", [])
                )
                self.candidate_feedback_answers = {}
                self.candidate_feedback_error = ""
                self.show_candidate_feedback_modal = True
            else:
                self.candidate_feedback_questions = []
                self.candidate_feedback_answers = {}
                self.candidate_feedback_error = ""
                self.show_candidate_feedback_modal = False

        except (ValueError, OSError) as exc:
            self.show_candidate_feedback_modal = False
            yield rx.toast.error(
                f"Unable to load candidate feedback: {exc}"
            )

        yield rx.toast.success(
            "Assessment submitted successfully!",
            duration=4000,
        )

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

    # Ã¢â€â‚¬Ã¢â€â‚¬ Candidate Test Feedback Methods Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
        """Load and open the pending Admin-created Candidate Feedback Form."""
        self.candidate_feedback_error = ""

        cand_id = self.candidate_id or "CAND-2031"

        if not self.active_assessment_id or not self.active_test_id:
            self.candidate_feedback_error = (
                "Unable to load feedback because assessment/test identity is missing."
            )
            return rx.toast.error(self.candidate_feedback_error)

        try:
            service = FeedbackService()

            form = service.pending_form(
                "candidate",
                cand_id,
                self.active_assessment_id,
                self.active_test_id,
            )

            if not form:
                self.candidate_feedback_questions = []
                self.candidate_feedback_answers = {}
                self.show_candidate_feedback_modal = False

                return rx.toast.info(
                    "No pending Candidate Feedback Form is available for this test."
                )

            self.candidate_feedback_questions = list(
                form.get("questions", [])
            )
            self.candidate_feedback_answers = {}
            self.candidate_feedback_error = ""
            self.show_candidate_feedback_modal = True

        except (ValueError, OSError) as exc:
            self.show_candidate_feedback_modal = False
            self.candidate_feedback_error = str(exc)
            return rx.toast.error(
                f"Unable to load candidate feedback: {exc}"
            )


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
        """Persist Candidate Feedback through the canonical FeedbackService."""
        if not self.candidate_feedback_questions:
            self.candidate_feedback_error = (
                "No candidate feedback form is available."
            )
            return

        missing_required = [
            question
            for question in self.candidate_feedback_questions
            if question.get("required", False)
            and not str(
                self.candidate_feedback_answers.get(
                    question["id"], ""
                )
            ).strip()
        ]

        if missing_required:
            self.candidate_feedback_error = (
                "Please complete all required questions before submitting."
            )
            return


        auth = await self.get_state(AuthState)

        if (
            not auth.is_candidate_authenticated
            or not auth.candidate_emp_id
            or self.candidate_id != auth.candidate_emp_id
        ):
            self.candidate_feedback_error = (
                "Your candidate session is invalid. Please sign in again."
            )
            yield rx.toast.error(self.candidate_feedback_error)
            return

        cand_id = auth.candidate_emp_id

        if not self.active_assessment_id or not self.active_test_id:
            self.candidate_feedback_error = (
                "Assessment or test identity is missing."
            )
            return

        try:
            service = FeedbackService()

            form = await asyncio.to_thread(
            service.pending_form,
            "candidate",
            cand_id,
            self.active_assessment_id,
            self.active_test_id,
        )

            if not form:
                self.candidate_feedback_error = (
                    "No pending feedback form is available."
                )
                return

            await asyncio.to_thread(
                service.submit,
                "candidate",
                cand_id,
                self.active_assessment_id,
                form["feedback_form_id"],
                dict(self.candidate_feedback_answers),
                self.active_test_id,
            )

        except (ValueError, OSError) as exc:
            self.candidate_feedback_error = str(exc)
            yield rx.toast.error(str(exc))
            return

        self.show_candidate_feedback_modal = False
        self.candidate_feedback_questions = []
        self.candidate_feedback_answers = {}
        self.candidate_feedback_error = ""

        yield rx.toast.success(
            "Feedback submitted successfully. Thank you!"
        )

        for action in self.return_to_dashboard():
            yield action


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


