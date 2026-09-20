"""Read-only safeguards for name-scoped test data; never deletes dependent data."""
import sys
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class TestDependencyService:
    def __init__(self, data_dir, upload_dir):
        self.data_dir = Path(data_dir)
        self.upload_dir = Path(upload_dir)

    def ensure_mutable(self, test, assessment):
        def matches(row):
            if row.get("test_id"):
                return row["test_id"] == test["test_id"]
            return (row.get("assessment_name") == assessment["name"]
                    and row.get("test_name") == test["test_name"])

        reasons = []
        paper = test.get("question_paper", "")
        if paper and (self.upload_dir / paper).is_file():
            reasons.append("question paper")
        for name in ("manual_evaluations.json", "ai_evaluation_runs.json", "test_candidates.json"):
            path = self.data_dir / name
            if path.exists() and any(matches(r) for r in JSONRepository(path).get_all()):
                reasons.append(name)
        # Candidate drafts/submissions currently live in this process as well as Excel.
        module = sys.modules.get("ai_hybrid_evaluator.state.candidate_state")
        if module and any(matches(r) for r in getattr(module, "PERSISTED_CANDIDATE_TEST_DATA", {}).values()):
            reasons.append("candidate attempt")
        for path in (self.upload_dir / "candidate_responses").glob("*.xlsx"):
            import pandas as pd
            try:
                with pd.ExcelFile(path) as book:
                    if "Submission" in book.sheet_names:
                        rows = pd.read_excel(book, sheet_name="Submission", dtype=str).fillna("").to_dict("records")
                        if any(matches(r) for r in rows):
                            reasons.append("candidate response")
                    else:
                        from ai_hybrid_evaluator.services.candidate_response_service import _safe_slug
                        if _safe_slug(test["test_name"]) in _safe_slug(path.stem):
                            reasons.append("legacy response with uncertain assessment ownership")
            except Exception as exc:
                raise ValueError("Cannot verify candidate response dependencies; repair the unreadable workbook first.") from exc
        if reasons:
            raise ValueError("Cannot delete or rename test because dependent data exists: " + ", ".join(sorted(set(reasons))))
