"""Question-paper persistence inside the existing test record (one active paper)."""
from copy import deepcopy
from datetime import datetime, timezone
from backend.repositories.test_repository import TestRepository


class QuestionPaperRepository:
    def __init__(self, tests=None):
        self.tests = tests or TestRepository()

    def get_by_test(self, test_id):
        test = self.tests.get_by_id(test_id)
        if test is None:
            raise ValueError("Test not found.")
        detail = test.get("question_paper_details")
        if detail is not None and not isinstance(detail, dict):
            raise ValueError("Invalid stored question-paper metadata.")
        if detail and detail.get("filename") == test.get("question_paper"):
            if detail.get("test_id") != test_id or detail.get("assessment_id") != test["assessment_id"]:
                raise ValueError("Invalid stored question-paper relationship.")
            if (not isinstance(detail.get("question_paper_id"), str)
                    or not isinstance(detail.get("questions"), list)
                    or not detail["questions"]
                    or not all(isinstance(q, dict) for q in detail["questions"])
                    or detail.get("question_count") != len(detail["questions"])
                    or not isinstance(detail.get("total_marks"), (int, float))):
                raise ValueError("Invalid stored question-paper metadata.")
            return deepcopy(detail)
        return None  # Legacy filename-only association remains readable by the service.

    def save_for_test(self, test_id, paper):
        test = self.tests.get_by_id(test_id)
        if test is None:
            raise ValueError("Test not found.")
        if paper is None:
            test["question_paper"] = ""
            test.pop("question_paper_details", None)
        else:
            if paper["test_id"] != test_id or paper["assessment_id"] != test["assessment_id"]:
                raise ValueError("Invalid question-paper relationship.")
            test["question_paper"] = paper["filename"]
            test["question_paper_details"] = deepcopy(paper)
        test["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.tests.save(test)  # Filename, questions and metadata share one atomic JSON write.
        return deepcopy(paper)
