"""Read-only safeguards for name-scoped test data; never deletes dependent data."""
import sys
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class TestDependencyService:
    def __init__(self, data_dir, upload_dir):
        self.data_dir = Path(data_dir)
        self.upload_dir = Path(upload_dir)

    def ensure_mutable(self, test, assessment, *, include_unscoped_legacy_responses=True):
        def matches(row):
            if row.get("test_id"):
                return row["test_id"] == test["test_id"]
            return (row.get("assessment_name") == assessment["name"]
                    and row.get("test_name") == test["test_name"])

        reasons = []
        # A question paper belongs to the test itself and can be cleaned up
        # when the test is deleted. Its presence alone must not block deletion.

        # Completed/in-progress candidate activity and evaluation data DO block
        # deletion. Plain "Assigned" rows do not.
        for name in ("manual_evaluations.json", "ai_evaluation_runs.json"):
            path = self.data_dir / name
            if path.exists() and any(matches(r) for r in JSONRepository(path).get_all()):
                reasons.append(name)

        candidate_path = self.data_dir / "test_candidates.json"
        if candidate_path.exists():
            candidate_rows = JSONRepository(candidate_path).get_all()
            if any(
                matches(r) and r.get("status") != "Assigned"
                for r in candidate_rows
            ):
                reasons.append("candidate attempt")
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
                        for row in rows:
                            if row.get("test_id"):
                                if matches(row):
                                    reasons.append("candidate response")
                                    break
                                continue

                            # Legacy response: no immutable test_id.
                            if not matches(row):
                                continue

                            # Do not let an old name-only response block a
                            # newly-created test that reused the same name.
                            created_at = test.get("created_at")
                            if created_at:
                                from datetime import datetime, timezone
                                test_created = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                                if test_created.tzinfo is None:
                                    test_created = test_created.replace(
                                        tzinfo=timezone.utc
                                    )

                                response_modified = datetime.fromtimestamp(
                                    path.stat().st_mtime,
                                    tz=timezone.utc,
                                )

                                if response_modified < test_created:
                                    continue

                            reasons.append("candidate response")
                            break
                    elif include_unscoped_legacy_responses:
                        from ai_hybrid_evaluator.services.candidate_response_service import _safe_slug
                        if _safe_slug(test["test_name"]) in _safe_slug(path.stem):
                            reasons.append("legacy response with uncertain assessment ownership")
            except Exception as exc:
                raise ValueError("Cannot verify candidate response dependencies; repair the unreadable workbook first.") from exc
        if reasons:
            raise ValueError("Cannot delete or rename test because dependent data exists: " + ", ".join(sorted(set(reasons))))
