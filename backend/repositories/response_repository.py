"""One response session per candidate/assessment/test, using the common JSON writer."""
from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class ResponseRepository:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else Path(__file__).resolve().parents[1] / "data" / "responses.json"

    @staticmethod
    def _validate(rows):
        pairs = []
        for row in rows:
            if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("candidate_id", "assessment_id", "test_id", "assessment_name", "test_name", "candidate_name")):
                raise ValueError("Invalid response identity in responses.json.")
            pairs.append((row["candidate_id"], row["assessment_id"], row["test_id"]))
            if row.get("status") not in ("In Progress", "Submitted", "Disqualified"):
                raise ValueError("Invalid response status in responses.json.")
            if not isinstance(row.get("answers"), dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in row["answers"].items()):
                raise ValueError("Invalid saved answers in responses.json.")
            marks = row.get("marked_for_review")
            if not isinstance(marks, list) or any(type(q) is not int or q < 1 for q in marks) or len(marks) != len(set(marks)):
                raise ValueError("Invalid review marks in responses.json.")
            if type(row.get("violation_count")) is not int or not 0 <= row["violation_count"] <= 3:
                raise ValueError("Invalid violation count in responses.json.")
            if not isinstance(row.get("questions"), list) or not row["questions"] or any(not isinstance(q, dict) for q in row["questions"]):
                raise ValueError("Invalid question snapshot in responses.json.")
            ids = [q.get("id") for q in row["questions"]]
            if any(type(q) is not int or q < 1 for q in ids) or len(ids) != len(set(ids)):
                raise ValueError("Invalid question IDs in responses.json.")
            if set(row["answers"]) - {str(q) for q in ids} or set(marks) - set(ids):
                raise ValueError("Saved answer/review question does not belong to the session.")
            if row.get("_pending_status") not in (None, row["status"]):
                raise ValueError("Invalid pending response transition.")
        if len(pairs) != len(set(pairs)):
            raise ValueError("Duplicate response session in responses.json.")

    def get_all(self):
        if not self.file_path.exists():
            return []
        rows = JSONRepository(self.file_path).get_all()
        self._validate(rows)
        return rows

    def get(self, candidate_id, assessment_id, test_id):
        return next((r for r in self.get_all() if (r["candidate_id"], r["assessment_id"], r["test_id"]) == (candidate_id, assessment_id, test_id)), None)

    def save(self, record):
        rows = self.get_all()
        key = tuple(record.get(k) for k in ("candidate_id", "assessment_id", "test_id"))
        rows = [r for r in rows if tuple(r[k] for k in ("candidate_id", "assessment_id", "test_id")) != key] + [deepcopy(record)]
        self._validate(rows)
        JSONRepository(self.file_path).save_all(rows)
        return deepcopy(record)

    def delete_by_test(self, assessment_id, test_id):
        """Delete response sessions belonging only to one assessment/test."""
        rows = self.get_all()

        remaining = [
            row
            for row in rows
            if not (
                row["assessment_id"] == assessment_id
                and row["test_id"] == test_id
            )
        ]

        self._validate(remaining)
        JSONRepository(self.file_path).save_all(remaining)

        return len(rows) - len(remaining)

