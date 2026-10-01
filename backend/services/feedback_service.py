"""Admin-defined surveys, independent of evaluation results and reports."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from backend.repositories.feedback_repository import FeedbackFormRepository, FeedbackResponseRepository
from backend.repositories.response_repository import ResponseRepository
from backend.services.assessment_service import _PERSISTENCE_LOCK
from backend.services.candidate_assignment_service import CandidateAssignmentService


def _now():
    return datetime.now(timezone.utc).isoformat()


class FeedbackService:
    def __init__(self, assignments=None, forms=None, responses=None):
        self.assignments = assignments or CandidateAssignmentService()
        self.assessments = self.assignments.assessments
        data = self.assignments.repository.file_path.parent
        self.forms = forms or FeedbackFormRepository(data/"feedback_forms.json")
        self.responses = responses or FeedbackResponseRepository(data/"feedback_responses.json")
        self.sessions = ResponseRepository(data/"responses.json")

    @staticmethod
    def _validate_form(value):
        if value.get("target_role") not in ("candidate", "facilitator"):
            raise ValueError("Feedback role must be candidate or facilitator.")
        for field in ("title", "assessment_id"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise ValueError(f"Feedback {field} is required.")
        if not isinstance(value.get("description", ""), str) or type(value.get("active", True)) is not bool:
            raise ValueError("Invalid feedback description or active flag.")
        questions = value.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("Add at least one feedback question.")
        ids = []
        for q in questions:
            if not isinstance(q, dict) or set(q) - {"id", "text", "type", "required"}:
                raise ValueError("Invalid feedback question definition.")
            if any(not isinstance(q.get(k), str) or not q[k].strip() for k in ("id", "text")):
                raise ValueError("Question ID and text are required.")
            if q.get("type", "textarea") not in ("text", "textarea"):
                raise ValueError("The current feedback builder supports text answers only.")
            if type(q.get("required", True)) is not bool:
                raise ValueError("Question required must be boolean.")
            ids.append(q["id"])
        if len(ids) != len(set(ids)):
            raise ValueError("Feedback question IDs must be unique.")

    def list_forms(self, assessment_id=None, target_role=None):
        return [r for r in self.forms.get_all() if (assessment_id is None or r["assessment_id"] == assessment_id)
                and (target_role is None or r["target_role"] == target_role)]

    def get_form(self, form_id):
        result = next((r for r in self.forms.get_all() if r["feedback_form_id"] == form_id), None)
        if result is None:
            raise ValueError("Feedback form does not exist.")
        self._validate_form(result)
        return result

    def resolve_form(self, assessment_id, role):
        self.assessments.get_assessment(assessment_id)
        if role not in ("candidate", "facilitator"):
            raise ValueError("Invalid feedback role.")
        rows = [r for r in self.list_forms(assessment_id, role) if r["active"]]
        if len(rows) > 1:
            raise ValueError("Multiple active feedback forms apply; ask Admin to resolve them.")
        if rows:
            self._validate_form(rows[0])
        return rows[0] if rows else None

    def save_form(self, details, form_id=None):
        with _PERSISTENCE_LOCK:
            allowed = {"title", "description", "assessment_id", "target_role", "questions", "active"}
            if not isinstance(details, dict) or set(details) - allowed:
                raise ValueError("Unsupported feedback form fields.")
            old = self.get_form(form_id) if form_id else {}
            value = {"description": "", "active": True, **old, **deepcopy(details)}
            self._validate_form(value)
            self.assessments.get_assessment(value["assessment_id"])
            if old and any(value[k] != old[k] for k in ("assessment_id", "target_role")):
                raise ValueError("Form ownership and role cannot be changed.")
            value["title"] = value["title"].strip()
            value["questions"] = [{"type": "textarea", "required": True, **q} for q in value["questions"]]
            if old and any(r["feedback_form_id"] == form_id for r in self.responses.get_all()):
                if any(value[k] != old[k] for k in ("title", "description", "questions")):
                    raise ValueError("This form has responses; its definition is read-only. Deactivate it before creating a replacement.")
            if value["active"] and any(r["active"] and r["feedback_form_id"] != form_id
                for r in self.list_forms(value["assessment_id"], value["target_role"])):
                raise ValueError("An active form already applies to this assessment and role.")
            stamp = _now()
            value.update(feedback_form_id=form_id or uuid4().hex, created_at=old.get("created_at", stamp), updated_at=stamp)
            return self.forms.save(value)

    def _context(self, role, respondent_id, assessment_id, test_id=None):
        assessment = self.assessments.get_assessment(assessment_id)
        if role == "candidate":
            assignment = self.assignments.get_test_assignment(respondent_id, test_id)
            if assignment["assessment_id"] != assessment_id:
                raise ValueError("Feedback test does not belong to this assessment.")
            respondent_id = assignment["candidate_id"]
            session = self.sessions.get(respondent_id, assessment_id, test_id)
            if assignment["status"] != "Submitted" or not session or session["status"] != "Submitted" or session.get("_pending_status"):
                raise ValueError("Candidate feedback is available only after successful test submission.")
        elif role == "facilitator":
            if test_id is not None:
                raise ValueError("Facilitator feedback is assessment-scoped, not test-scoped.")
            known = {r["emp_id"] for r in self.assessments._facilitators()}
            assigned = assessment.get("facilitator_ids") or ([assessment["facilitator_id"]] if assessment.get("facilitator_id") else [])
            if respondent_id not in known or respondent_id not in assigned:
                raise ValueError("Facilitator is not authorized for this assessment.")
        else:
            raise ValueError("Invalid feedback role.")
        return respondent_id

    @staticmethod
    def _key(role, respondent_id, aid, tid, form_id):
        return {"respondent_role": role, "candidate_id": respondent_id if role == "candidate" else None,
                "facilitator_id": respondent_id if role == "facilitator" else None,
                "assessment_id": aid, "test_id": tid, "feedback_form_id": form_id}

    def list_responses(self, **filters):
        allowed = {"respondent_role", "candidate_id", "facilitator_id", "assessment_id", "test_id", "feedback_form_id"}
        if set(filters) - allowed:
            raise ValueError("Unsupported feedback filter.")
        return [r for r in self.responses.get_all() if all(r.get(k) == v for k, v in filters.items())]

    def pending_form(self, role, respondent_id, assessment_id, test_id=None):
        with _PERSISTENCE_LOCK:
            respondent_id = self._context(role, respondent_id, assessment_id, test_id)
            form = self.resolve_form(assessment_id, role)
            if form and not self.list_responses(**self._key(role, respondent_id, assessment_id, test_id, form["feedback_form_id"])):
                return form
            return None

    def submit(self, role, respondent_id, assessment_id, form_id, answers, test_id=None):
        with _PERSISTENCE_LOCK:
            respondent_id = self._context(role, respondent_id, assessment_id, test_id)
            form = self.get_form(form_id)
            if form["assessment_id"] != assessment_id or form["target_role"] != role:
                raise ValueError("Feedback form does not apply to this respondent/assessment.")
            key = self._key(role, respondent_id, assessment_id, test_id, form_id)
            old = self.list_responses(**key)
            if old:
                return old[0]  # First successful submission is final; retries cannot overwrite it.
            active = self.resolve_form(assessment_id, role)
            if not active or active["feedback_form_id"] != form_id:
                raise ValueError("Feedback form changed or is inactive; reopen the form.")
            if not isinstance(answers, dict) or set(answers) - {q["id"] for q in form["questions"]}:
                raise ValueError("Invalid feedback question IDs.")
            cleaned = {}
            for q in form["questions"]:
                value = answers.get(q["id"], "")
                if not isinstance(value, str):
                    raise ValueError("Feedback answers must be text.")
                if q["required"] and not value.strip():
                    raise ValueError("Please complete all required feedback questions.")
                cleaned[q["id"]] = value.strip()
            return self.responses.save({**key, "feedback_response_id": uuid4().hex, "answers": cleaned, "submitted_at": _now()})

    def close_assessment(self, facilitator_id, assessment_id):
        """Retry-safe: a saved survey remains saved if the later lifecycle write fails."""
        with _PERSISTENCE_LOCK:
            if self.pending_form("facilitator", facilitator_id, assessment_id):
                raise ValueError("Submit the required facilitator feedback before closing this assessment.")
            current = self.assessments.get_assessment(assessment_id)
            if current["status"] == "Completed":
                return current
            return self.assessments.update_lifecycle(assessment_id, status="Completed")

    def response_views(self):
        """Resolve names once per page load; never read repositories inside the row loop."""
        forms = {f["feedback_form_id"]: f for f in self.forms.get_all()}
        assessments = {a["assessment_id"]: a for a in self.assessments.repository.get_all()}
        tests = {t["test_id"]: t for t in self.assessments.tests.repository.get_all()}
        candidates = {c["candidate_id"]: c for c in self.assignments.candidates.list_candidates()}
        facilitators = {f["emp_id"]: f for f in self.assessments._facilitators()}
        views = []
        for r in self.responses.get_all():
            form = forms.get(r["feedback_form_id"])
            if not form:
                raise ValueError("Feedback response references a missing form.")
            views.append({**r, "form_title": form["title"], "assessment": assessments.get(r["assessment_id"], {}).get("name", r["assessment_id"]),
                "test": tests.get(r["test_id"], {}).get("test_name", ""),
                "candidate_name": candidates.get(r["candidate_id"], {}).get("name", r["candidate_id"] or ""),
                "facilitator": facilitators.get(r["facilitator_id"], {}).get("name", r["facilitator_id"] or ""),
                "qa_pairs": [{"question": q["text"], "answer": r["answers"].get(q["id"], "")} for q in form["questions"]]})
        return views
