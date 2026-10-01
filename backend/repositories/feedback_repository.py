"""Survey-only stores. Reads never create files or migrate legacy evaluation comments."""
from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class FeedbackRepository:
    def __init__(self, file_path, identity):
        self.file_path = Path(file_path)
        self.identity = identity

    def _validate(self, rows):
        ids = [r.get(self.identity) for r in rows]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Invalid or duplicate feedback identity.")
        if self.identity == "feedback_response_id":
            keys = [(r.get("feedback_form_id"), r.get("respondent_role"), r.get("candidate_id"),
                     r.get("facilitator_id"), r.get("assessment_id"), r.get("test_id")) for r in rows]
            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate feedback response.")

    def get_all(self):
        rows = JSONRepository(self.file_path).get_all() if self.file_path.exists() else []
        self._validate(rows)
        return rows

    def save(self, row):
        rows = [r for r in self.get_all() if r[self.identity] != row[self.identity]] + [deepcopy(row)]
        self._validate(rows)
        JSONRepository(self.file_path).save_all(rows)
        return deepcopy(row)


class FeedbackFormRepository(FeedbackRepository):
    def __init__(self, file_path=None):
        super().__init__(file_path or Path(__file__).resolve().parents[1]/"data"/"feedback_forms.json", "feedback_form_id")


class FeedbackResponseRepository(FeedbackRepository):
    def __init__(self, file_path=None):
        super().__init__(file_path or Path(__file__).resolve().parents[1]/"data"/"feedback_responses.json", "feedback_response_id")
