"""Durable response lifecycle, with assignment status owned by CandidateAssignmentService."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from uuid import uuid4
import random
from backend.repositories.response_repository import ResponseRepository
from backend.services.assessment_service import _PERSISTENCE_LOCK
from backend.services.candidate_assignment_service import CandidateAssignmentService


def _now():
    return datetime.now(timezone.utc).isoformat()


class ResponseLifecycleService:
    def __init__(self, assignments=None, repository=None, question_loader=None, excel_writer=None):
        self.assignments = assignments or CandidateAssignmentService()
        self.repository = repository or ResponseRepository(self.assignments.repository.file_path.parent / "responses.json")
        self.question_loader = question_loader or self._load_questions
        if excel_writer is None:
            from ai_hybrid_evaluator.services.candidate_response_service import save_candidate_response
            excel_writer = save_candidate_response
        self.excel_writer = excel_writer

    def _load_questions(self, assessment_id, test_id):
        from backend.services.question_paper_service import QuestionPaperService
        papers = QuestionPaperService(self.assignments.assessments.tests, self.assignments.candidates.dependencies.upload_dir)
        rows = papers.get_questions(assessment_id, test_id)
        kind = self.assignments.assessments.tests.get_test(test_id, assessment_id).get("test_type")
        return [{"id": int(float(str(r["Question No"]).strip().removeprefix("Q"))), "title": str(r["Question No"]),
                 "text": r["Question"], "marks": r["Marks"], "co": r["CO"], "lo": r["LO"],
                 "knowledge_type": r["Knowledge Type"], "category": r["Domain"], "rbt_level": r["RBT level"],
                 "question_type": "Objective" if kind == "objective" else "Subjective",
                 "question_stem": r.get("question_stem", r["Question"]),
                 "options": deepcopy(r.get("options", {})) if kind == "objective" else {}} for r in rows]

    def _identity(self, candidate_id, assessment_id, test_id):
        assignment = self.assignments.get_test_assignment(candidate_id, test_id)
        if assignment["assessment_id"] != assessment_id:
            raise ValueError("Response test does not belong to this assessment.")
        return assignment

    def _transition(self, record, target):
        # Save intent first: a crash between JSON stores is completed on the next read.
        pending = {**record, "status": target, "_pending_status": target, "updated_at": _now()}
        self.repository.save(pending)
        return self._complete_transition(pending)

    def _complete_transition(self, pending):
        target = pending["_pending_status"]
        if target == "Submitted" and not Path(pending.get("response_file") or "").is_file():
            raise ValueError("Cannot finalize submission: the response workbook is missing.")
        assignment = self.assignments.update_test_status(pending["candidate_id"], pending["test_id"], target)
        result = {**pending, "started_at": assignment["started_at"], "updated_at": _now()}
        if target == "Submitted":
            result["submitted_at"] = assignment["submitted_at"]
        result.pop("_pending_status")
        return self.repository.save(result)

    def _read(self, candidate_id, assessment_id, test_id, required=False):
        assignment = self._identity(candidate_id, assessment_id, test_id)
        record = self.repository.get(assignment["candidate_id"], assessment_id, test_id)
        if record is None:
            if required:
                raise ValueError("Response session does not exist; start the assigned test first.")
            return None, assignment
        if record.get("_pending_status"):
            record = self._complete_transition(record)
            assignment = self._identity(candidate_id, assessment_id, test_id)
        if record["status"] != assignment["status"]:
            raise ValueError("Response and assignment status differ; resolve the stored lifecycle before continuing.")
        return record, assignment

    def get_response(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            return self._read(candidate_id, assessment_id, test_id)[0]

    def get_latest_response(self, candidate_id, assessment_id, test_id):
        return self.get_response(candidate_id, assessment_id, test_id)

    def get_status(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            record, assignment = self._read(candidate_id, assessment_id, test_id)
            return record["status"] if record else assignment["status"]

    def get_answers(self, candidate_id, assessment_id, test_id):
        return (self.get_response(candidate_id, assessment_id, test_id) or {}).get("answers", {})

    def get_submission_metadata(self, candidate_id, assessment_id, test_id):
        record = self.get_response(candidate_id, assessment_id, test_id)
        return {k: record[k] for k in ("status", "submission_receipt", "submitted_at", "response_file")} if record else {}

    def start_test(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            record, assignment = self._read(candidate_id, assessment_id, test_id)
            if assignment["status"] in ("Submitted", "Disqualified"):
                raise ValueError("Submitted or disqualified tests cannot be restarted.")
            if record:
                return record
            questions = deepcopy(self.question_loader(assessment_id, test_id))

            # Preserve the original question-paper order for every candidate.
            # No question shuffling is performed for Objective or Subjective
            # questions. Stable question IDs continue to map answers correctly.

            fields = {"id", "title", "text", "marks", "co", "lo", "knowledge_type", "category", "rbt_level"}
            if not questions or any(not isinstance(q, dict) or fields - q.keys() or type(q["id"]) is not int or q["id"] < 1 for q in questions):
                raise ValueError("A valid question paper is required before starting the test.")
            if len({q["id"] for q in questions}) != len(questions):
                raise ValueError("Duplicate question IDs in the test paper.")
            test = self.assignments.assessments.tests.get_test(test_id, assessment_id)
            assessment = self.assignments.assessments.get_assessment(assessment_id)
            candidate = self.assignments.candidates.get_candidate(assignment["candidate_id"])
            stamp = _now()
            record = {"candidate_id": assignment["candidate_id"], "candidate_name": candidate["name"],
                      "assessment_id": assessment_id, "test_id": test_id, "assessment_name": assessment["name"],
                      "test_name": test["test_name"], "status": "In Progress", "answers": {}, "marked_for_review": [],
                      "violation_count": 0, "submission_receipt": "", "started_at": assignment["started_at"] or stamp,
                      "submitted_at": None, "created_at": stamp, "updated_at": stamp, "response_file": "",
                      "test_type": test.get("test_type"),
                      "questions": [{**{k: q[k] for k in fields},
                                     **{k: deepcopy(q[k]) for k in ("options", "question_type", "question_stem") if k in q}} for q in questions]}
            return self._transition(record, "In Progress")

    def resume_test(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            return self._editable(candidate_id, assessment_id, test_id)

    def _editable(self, candidate_id, assessment_id, test_id):
        record, _ = self._read(candidate_id, assessment_id, test_id, required=True)
        if record["status"] != "In Progress":
            raise ValueError("Submitted or disqualified responses cannot be modified or submitted again.")
        return record

    @staticmethod
    def _question_id(record, question_id):
        try:
            if isinstance(question_id, bool) or str(question_id).strip() != str(int(question_id)):
                raise ValueError()
            identity = int(question_id)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Invalid question ID.") from None
        if identity not in {q["id"] for q in record["questions"]}:
            raise ValueError("Question does not belong to this response session.")
        return identity

    def _answers(self, record, answers, clear=False):
        if not isinstance(answers, dict) or not isinstance(clear, bool):
            raise ValueError("Answers must be a question-to-text mapping.")
        for key, text in answers.items():
            identity = str(self._question_id(record, key))
            if not isinstance(text, str):
                raise ValueError("Answer text must be a string.")
            if not text.strip() and record["answers"].get(identity, "").strip() and not clear:
                continue
            record["answers"][identity] = text
        return record

    def _save(self, record):
        record["updated_at"] = _now()
        return self.repository.save(record)

    def save_answer(self, candidate_id, assessment_id, test_id, question_id, text, *, clear=False):
        with _PERSISTENCE_LOCK:
            record = self._editable(candidate_id, assessment_id, test_id)
            return self._save(self._answers(record, {question_id: text}, clear))

    def mark_for_review(self, candidate_id, assessment_id, test_id, question_id, marked=True):
        with _PERSISTENCE_LOCK:
            record = self._editable(candidate_id, assessment_id, test_id)
            identity = self._question_id(record, question_id)
            if not isinstance(marked, bool):
                raise ValueError("Review mark must be true or false.")
            current = set(record["marked_for_review"])
            if marked: current.add(identity)
            else: current.discard(identity)
            record["marked_for_review"] = sorted(current)
            return self._save(record)

    def update_violation_count(self, candidate_id, assessment_id, test_id, count):
        with _PERSISTENCE_LOCK:
            record = self._editable(candidate_id, assessment_id, test_id)
            if type(count) is not int or count < record["violation_count"]:
                raise ValueError("Violation count must be a nonnegative integer and cannot decrease.")
            record["violation_count"] = min(count, 3)
            if record["violation_count"] == 3:
                return self._disqualify(record)
            return self._save(record)

    def record_violation(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            record = self._editable(candidate_id, assessment_id, test_id)
            return self.update_violation_count(candidate_id, assessment_id, test_id, record["violation_count"] + 1)

    def _disqualify(self, record):
        stamp = _now()
        record.update({"submitted_at": stamp, "terminated_at": stamp, "submission_receipt": "DQ-" + uuid4().hex})
        return self._transition(record, "Disqualified")

    def disqualify(self, candidate_id, assessment_id, test_id):
        with _PERSISTENCE_LOCK:
            return self._disqualify(self._editable(candidate_id, assessment_id, test_id))

    @staticmethod
    def _safe_artifact_name(value):
        # The unchanged Excel writer uses these strings as filename components.
        if not value or PureWindowsPath(value).name != value or any(c in value for c in '/\\:<>"|?*'):
            raise ValueError("Candidate/test name is not safe for the existing response workbook filename.")

    def submit(self, candidate_id, assessment_id, test_id, *, answers=None, clear=False, reason="submitted"):
        with _PERSISTENCE_LOCK:
            record = self._editable(candidate_id, assessment_id, test_id)
            if reason not in ("submitted", "time_expired"):
                raise ValueError("Invalid submission reason.")
            if answers is not None:
                record = self._save(self._answers(record, answers, clear))
            # Display names may change during a session; resolve them using stable IDs.
            record["assessment_name"] = self.assignments.assessments.get_assessment(assessment_id)["name"]
            record["test_name"] = self.assignments.assessments.tests.get_test(test_id, assessment_id)["test_name"]
            record["candidate_name"] = self.assignments.candidates.get_candidate(record["candidate_id"])["name"]
            self._safe_artifact_name(record["candidate_name"])
            self._safe_artifact_name(record["test_name"])
            output_dir = (Path("uploaded_files") / "candidate_responses").resolve()
            existing_files = set(output_dir.glob("*.xlsx"))
            try:
                filename = self.excel_writer(candidate_id=record["candidate_id"], candidate_name=record["candidate_name"],
                    assessment_name=record["assessment_name"], test_name=record["test_name"],
                    questions=deepcopy(record["questions"]), answers=deepcopy(record["answers"]))
                path = Path(filename).resolve()
                if path.parent != output_dir or not path.is_file():
                    raise ValueError("Response workbook was not created in the expected directory.")
            except Exception as exc:
                raise ValueError("Unable to save the Excel response; the test has not been submitted.") from exc
            record.update({"response_file": str(path), "submitted_at": _now(), "submission_receipt": "SUB-" + uuid4().hex,
                           "submission_reason": reason})
            try:
                return self._transition(record, "Submitted")
            except (ValueError, OSError):
                # Delete only this newly generated artifact if no durable intent exists.
                stored = self.repository.get(record["candidate_id"], assessment_id, test_id)
                if stored and stored.get("response_file") != str(path) and path not in existing_files:
                    path.unlink(missing_ok=True)
                raise

    def handle_time_expired(self, candidate_id, assessment_id, test_id, *, answers=None):
        return self.submit(candidate_id, assessment_id, test_id, answers=answers, reason="time_expired")
