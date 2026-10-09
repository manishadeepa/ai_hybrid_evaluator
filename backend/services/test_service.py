from copy import deepcopy
from uuid import uuid4
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from backend.repositories.assessment_repository import AssessmentRepository
from backend.services.test_dependency_service import TestDependencyService
from backend.repositories.test_repository import TestRepository
from backend.repositories.response_repository import ResponseRepository
from backend.services.question_type_schema import validate_test_type


class TestService:
    """Keep stable test identities while adapting existing name-based UI fields."""

    def __init__(self, repository=None, assessment_repository=None, upload_dir=None):
        self.repository = repository or TestRepository()
        self.assessments = assessment_repository or AssessmentRepository(self.repository.file_path.parent / "assessments.json")
        uploads = upload_dir or ((Path(__file__).resolve().parents[2] / "uploaded_files") if repository is None
                                 else self.repository.file_path.parent / "uploaded_files")
        self.dependencies = TestDependencyService(self.repository.file_path.parent, uploads)

    @staticmethod
    def _lock():
        # Use the same lock as assessment edits, including their test-list updates.
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        return _PERSISTENCE_LOCK

    def get_assessment(self, test_id):
        return self._assessment(self.get_test(test_id)["assessment_id"])

    def _assessment(self, assessment_id):
        if not isinstance(assessment_id, str) or not assessment_id.strip():
            raise ValueError("Assessment ID is required.")
        record = self.assessments.get_by_id(assessment_id)
        if record is None:
            raise ValueError("Assessment not found.")
        return record

    def get_test(self, test_id, assessment_id=None):
        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError("Test ID is required.")
        record = self.repository.get_by_id(test_id)
        if record is None:
            raise ValueError("Test not found.")
        if assessment_id is not None and record["assessment_id"] != assessment_id:
            raise ValueError("Test does not belong to this assessment.")
        self._assessment(record["assessment_id"])
        return {"status": "Draft", "is_final": False, "position": 0, **record}

    def list_tests(self, assessment_id=None):
        # One fresh snapshot per call; never cache authorization across requests.
        with self._lock():
            assessments = {r["assessment_id"] for r in self.assessments.get_all()}
            if assessment_id is not None:
                if not isinstance(assessment_id, str) or not assessment_id.strip():
                    raise ValueError("Assessment ID is required.")
                if assessment_id not in assessments:
                    raise ValueError("Assessment not found.")
            results = []
            for record in self.repository.get_all():
                if assessment_id is not None and record["assessment_id"] != assessment_id:
                    continue
                if not isinstance(record.get("test_id"), str) or not record["test_id"].strip():
                    raise ValueError("Test ID is required.")
                if record["assessment_id"] not in assessments:
                    raise ValueError("Assessment not found.")
                results.append({"status": "Draft", "is_final": False, "position": 0, **record})
            return results

    @staticmethod
    def _validate_not_past_date(raw):
        """Reject valid calendar dates earlier than today in the app's IST timezone."""
        if not raw:
            return
        parsed = None
        for fmt in ("%Y-%m-%d", "%d %b %Y"):
            try:
                parsed = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        # Keep legacy free-text dates readable through aggregate assessment edits.
        if parsed is not None and parsed < datetime.now(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("Test date cannot be earlier than today.")

    @staticmethod
    def _validate_fields(value):
        if "test_type" in value:
            validate_test_type(value["test_type"])
        name = value.get("test_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Test name is required.")
        value["test_name"] = name.strip()
        if value.get("status", "Draft") not in ("Draft", "Scheduled", "Active", "Completed"):
            raise ValueError("Invalid test status; use Draft, Scheduled, Active or Completed.")
        if not isinstance(value.get("is_final", False), bool):
            raise ValueError("Invalid test type.")
        for field in ("description", "question_paper"):
            if not isinstance(value.get(field, ""), str):
                raise ValueError(f"Invalid {field}.")
        raw = value.get("date", "")
        if not isinstance(raw, str):
            raise ValueError("Invalid test date.")
        if raw:
            for fmt in ("%Y-%m-%d", "%d %b %Y"):
                try:
                    datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    pass
            else:
                raise ValueError("Invalid test date; use YYYY-MM-DD or DD Mon YYYY.")
            TestService._validate_not_past_date(raw)

    def _unique(self, value):
        for row in self.get_tests(value["assessment_id"]):
            if row["test_id"] == value["test_id"]:
                continue
            if row["test_name"].strip().casefold() == value["test_name"].casefold():
                raise ValueError("Test already exists within this assessment.")
            if row.get("is_final", False) and value.get("is_final", False):
                raise ValueError("Assessment already has a final test.")

    def create_test(self, assessment_id, details):
        with self._lock():
            self._assessment(assessment_id)
            if not isinstance(details, dict):
                raise ValueError("Test details must be an object.")
            self._allowed(details)
            identity = details.get("test_id", uuid4().hex)
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError("Test ID is required.")
            if self.repository.get_by_id(identity):
                raise ValueError("Test ID already exists.")
            if details.get("assessment_id", assessment_id) != assessment_id:
                raise ValueError("Invalid assessment/test relationship.")
            stamp = datetime.now(timezone.utc).isoformat()
            value = {"date": "", "description": "", "question_paper": "", "status": "Draft", "is_final": False,
                     **deepcopy(details), "test_id": identity, "assessment_id": assessment_id,
                     "position": max((r.get("position", 0) for r in self.get_tests(assessment_id)), default=-1) + 1,
                     "created_at": stamp, "updated_at": stamp}
            self._validate_fields(value)
            self._check_type_change({}, value)
            self._unique(value)
            from backend.repositories.test_candidate_repository import TestCandidateRepository
            from backend.services.candidate_assignment_service import CandidateAssignmentService
            assignments = TestCandidateRepository(self.repository.file_path.parent / "test_candidates.json")
            planned = CandidateAssignmentService.plan_assessment_assignments(
                self._assessment(assessment_id), self.get_tests(assessment_id) + [value], assignments)
            previous_tests = self.repository.get_all()
            self.repository.save(value)
            try:
                if planned != assignments.get_all():
                    assignments.save_all(planned)
            except (ValueError, OSError):
                self.repository.save_all(previous_tests)
                raise
            return deepcopy(value)

    @staticmethod
    def _allowed(details):
        if set(details) - {"test_id", "assessment_id", "test_name", "description", "date", "status", "is_final", "question_paper", "test_type", "start_time", "end_time"}:
            raise ValueError("Unsupported test settings; availability is derived from the question paper and duration is fixed.")

    def update_test(self, test_id, changes):
        with self._lock():
            previous = self.get_test(test_id)
            if not isinstance(changes, dict):
                raise ValueError("Test changes must be an object.")
            self._allowed(changes)
            if any(changes.get(k, previous[k]) != previous[k] for k in ("test_id", "assessment_id")):
                raise ValueError("Test ID and assessment ownership cannot be changed.")
            value = {**previous, **deepcopy(changes)}
            # Historical free-text dates remain readable; validate only explicitly changed dates.
            checked = dict(value)
            if "date" not in changes or changes.get("date") == previous.get("date", ""):
                checked["date"] = ""
            self._validate_fields(checked)
            self._check_type_change(previous, value)
            value["test_name"] = checked["test_name"]
            self._unique(value)
            if value["test_name"] != previous["test_name"]:
                self.dependencies.ensure_mutable(previous, self._assessment(previous["assessment_id"]))
            value["updated_at"] = datetime.now(timezone.utc).isoformat()
            return self.repository.save(value)

    def get_availability(self, test_id):
        test = self.get_test(test_id)
        # The existing candidate UI uses the presence of a question-paper association.
        return bool(test.get("question_paper"))

    def _check_type_change(self, previous, value):
        """Legacy omission stays unknown; an explicit selection must fit its paper."""
        kind = value.get("test_type")
        if kind is None:
            return
        validate_test_type(kind)
        changed = previous.get("test_type") != kind
        if previous and changed:
            self.dependencies.ensure_mutable(previous, self._assessment(value["assessment_id"]))
        if value.get("question_paper") and (changed or previous.get("question_paper") != value["question_paper"]):
            from backend.services.question_paper_service import QuestionPaperService
            papers = QuestionPaperService(self)
            try:
                data = papers._path(value["question_paper"]).read_bytes()
            except OSError as exc:
                raise ValueError("Question-paper file is missing or unreadable; cannot verify test type.") from exc
            papers.validate_workbook(data, value["question_paper"], kind)


    def get_tests(self, assessment_id):
        return sorted((r for r in self.repository.get_all() if r["assessment_id"] == assessment_id),
                      key=lambda r: r.get("position", 0))

    def prepare_tests(self, assessment_id, assessment):
        old = self.get_tests(assessment_id)
        by_id = {r["test_id"]: r for r in old}
        by_name = {r["test_name"]: r for r in old}
        names = list(assessment.get("tests", []))
        final = assessment.get("final_test", "")
        if final:
            names.append(final)
        if any(not isinstance(n, str) or not n.strip() for n in names) or len(names) != len({n.strip().casefold() for n in names}):
            raise ValueError("Test names must be nonempty and unique within the assessment.")
        prepared = []
        used = set()
        for position, name in enumerate(names):
            requested_id = assessment.get("test_ids", {}).get(name)
            previous = by_id.get(requested_id) if requested_id else by_name.get(name)
            if requested_id and previous is None:
                raise ValueError("Unknown test identity for this assessment; reload before editing.")
            record = deepcopy(previous or {})
            test_id = record.get("test_id") or uuid4().hex
            if test_id in used:
                raise ValueError("Duplicate test identity.")
            used.add(test_id)
            record.update({"test_id": test_id, "assessment_id": assessment_id,
                           "test_name": name, "position": position, "is_final": name == final,
                           "date": assessment.get("test_dates", {}).get(name, ""),
                           "description": assessment.get("test_descriptions", {}).get(name, ""),
                           "question_paper": assessment.get("question_papers", {}).get(name, "")})
            timings = assessment.get("test_timings", {}).get(name, {})
            if isinstance(timings, dict):
                if "start_time" in timings:
                    record["start_time"] = timings.get("start_time", "")
                if "end_time" in timings:
                    record["end_time"] = timings.get("end_time", "")
            record.setdefault("status", "Draft")
            if previous is None or record.get("date", "") != previous.get("date", ""):
                self._validate_not_past_date(record.get("date", ""))
            types = assessment.get("test_types", {})
            if not isinstance(types, dict):
                raise ValueError("test_types must be an object.")
            if name in types:
                validate_test_type(types[name])
                record["test_type"] = types[name]
            self._check_type_change(previous or {}, record)
            if previous is None:
                record["created_at"] = datetime.now(timezone.utc).isoformat()
                record["updated_at"] = record["created_at"]
            elif record != previous:
                record["updated_at"] = datetime.now(timezone.utc).isoformat()
            prepared.append(record)
        if old:
            assessment_record = self._assessment(assessment_id)
            retained = {r["test_id"]: r for r in prepared}
            for previous in old:
                current = retained.get(previous["test_id"])
                if current is None or current["test_name"] != previous["test_name"]:
                    self.dependencies.ensure_mutable(previous, assessment_record)
        return prepared

    def replace_tests(self, assessment_id, records):
        if any(r.get("assessment_id") != assessment_id for r in records):
            raise ValueError("Invalid assessment/test relationship.")
        others = [r for r in self.repository.get_all() if r["assessment_id"] != assessment_id]
        self.repository.save_all(others + records)

    def delete_test(self, assessment_id, test_id, renumber=False):
        with self._lock():
            # Confirm that this exact test belongs to this exact assessment.
            target = self.get_test(test_id, assessment_id)
            assessment = self._assessment(assessment_id)

            # Never delete a test that already has candidate activity,
            # responses, or evaluation data.
            self.dependencies.ensure_mutable(target, assessment)

            # Deletion is explicitly allowed for the selected test.
            # Other assessments/tests are not affected because all cleanup
            # uses the immutable assessment_id + test_id ownership.
            records = [
                r
                for r in self.get_tests(assessment_id)
                if r["test_id"] != test_id
            ]

            number = 0
            for position, record in enumerate(records):
                record["position"] = position

                if renumber and not record.get("is_final", False):
                    number += 1
                    name = f"Formative {number}"

                    if name != record["test_name"]:
                        self.dependencies.ensure_mutable(record, assessment)
                        record["test_name"] = name

            # Remove the selected test from the assessment.
            self.replace_tests(assessment_id, records)

            # Remove candidate assignment rows belonging to the deleted test.
            from backend.repositories.test_candidate_repository import (
                TestCandidateRepository,
            )

            candidate_repository = TestCandidateRepository(
                self.repository.file_path.parent / "test_candidates.json"
            )
            candidate_repository.delete_by_test(test_id)

            # Remove response/attempt records belonging ONLY to this exact
            # assessment + test.
            response_repository = ResponseRepository(
                self.repository.file_path.parent / "responses.json"
            )
            response_repository.delete_by_test(assessment_id, test_id)

            return target

    def delete_assessment_tests(self, assessment_id):
        self.replace_tests(assessment_id, [])

    def populate_assessment(self, assessment, records=None):
        result = deepcopy(assessment)
        records = (self.get_tests(result["assessment_id"]) if records is None else
                   sorted(records, key=lambda r: r.get("position", 0)))
        result.update({"tests": [r["test_name"] for r in records if not r.get("is_final", False)],
                       "final_test": next((r["test_name"] for r in records if r.get("is_final", False)), ""),
                       "test_ids": {r["test_name"]: r["test_id"] for r in records},
                       "test_types": {r["test_name"]: r["test_type"] for r in records if "test_type" in r},
                       "test_dates": {r["test_name"]: r.get("date", "") for r in records},
                       "test_descriptions": {r["test_name"]: r.get("description", "") for r in records},
                       "question_papers": {r["test_name"]: r["question_paper"] for r in records if r.get("question_paper")},
                       "test_timings": {
                           r["test_name"]: {
                               "start_time": r.get("start_time", ""),
                               "end_time": r.get("end_time", ""),
                           }
                           for r in records
                           if r.get("start_time") or r.get("end_time")
                       }})
        return result


