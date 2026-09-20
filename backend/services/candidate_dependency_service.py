"""Read-only candidate deletion safeguards across the current data stores."""
import json
from pathlib import Path
import sys
from backend.repositories.json_repository import JSONRepository


class CandidateDependencyService:
    def __init__(self, data_dir, upload_dir, app_data_dir):
        self.data_dir, self.upload_dir, self.app_data_dir = map(Path, (data_dir, upload_dir, app_data_dir))

    def ensure_deletable(self, candidate, assessments, test_assignments):
        identity = candidate["candidate_id"]
        def matches(row):
            return row.get("candidate_id") == identity or identity in row.get("candidate_ids", [])
        if any(identity in a.get("assigned_candidates", []) for a in assessments):
            raise ValueError("Candidate cannot be deleted because assessment assignments exist.")
        if any(matches(r) for r in test_assignments):
            raise ValueError("Candidate cannot be deleted because test assignments exist.")
        for name in ("manual_evaluations.json", "ai_evaluation_runs.json"):
            path = self.data_dir / name
            if path.exists() and any(matches(r) for r in JSONRepository(path).get_all()):
                raise ValueError("Candidate cannot be deleted because evaluation data exists.")
        for name in ("candidate_feedbacks.json", "facilitator_feedbacks.json"):
            path = self.app_data_dir / name
            if path.exists():
                try:
                    records = json.loads(path.read_text(encoding="utf-8-sig"))
                except (ValueError, UnicodeError) as exc:
                    raise ValueError("Cannot verify candidate dependencies: unreadable feedback data.") from exc
                if not isinstance(records, dict):
                    raise ValueError("Cannot verify candidate dependencies: invalid feedback data.")
                if any(str(key).split(":")[-1] == identity or (isinstance(value, dict) and matches(value)) for key, value in records.items()):
                    raise ValueError("Candidate cannot be deleted because feedback data exists.")
        module = sys.modules.get("ai_hybrid_evaluator.state.candidate_state")
        if module and any(matches(r) for r in getattr(module, "PERSISTED_CANDIDATE_TEST_DATA", {}).values()):
            raise ValueError("Candidate cannot be deleted because a test attempt exists.")
        for path in (self.upload_dir / "candidate_responses").glob("*.xlsx"):
            import pandas as pd
            try:
                with pd.ExcelFile(path) as book:
                    if "Submission" in book.sheet_names:
                        rows = pd.read_excel(book, sheet_name="Submission", dtype=str).fillna("").to_dict("records")
                        found = any(matches(r) for r in rows)
                    else:
                        from ai_hybrid_evaluator.services.candidate_response_service import _safe_slug
                        found = any(_safe_slug(v) in _safe_slug(path.stem) for v in (identity, candidate["name"]))
            except Exception as exc:
                raise ValueError("Cannot verify candidate dependencies: unreadable response workbook.") from exc
            if found:
                raise ValueError("Candidate cannot be deleted because candidate responses exist.")
