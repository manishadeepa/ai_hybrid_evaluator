"""Evaluation progress derived from finalized, identity-scoped result records."""

def summarize_evaluation(assessment_id, test_id, candidate_ids, results, *, candidate_id=None, active=False):
    assigned = {value.strip() for value in candidate_ids if isinstance(value, str) and value.strip()}
    scope = assigned if candidate_id is None else ({candidate_id} if candidate_id in assigned else set())
    completed = {str(row.get("candidate_id", "")) for row in results
                 if isinstance(row, dict) and assessment_id and test_id and row.get("assessment_id") == assessment_id and row.get("test_id") == test_id
                 and row.get("evaluation_status") == "completed"
                 and str(row.get("candidate_id", "")) in scope}
    total = len(scope)
    status = ("Completed" if total and len(completed) == total else
              "In Progress" if completed or (active and total) else "Pending")
    return {"status": status, "completed": len(completed), "total": total}
