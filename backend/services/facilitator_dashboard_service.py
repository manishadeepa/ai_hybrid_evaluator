"""Read-only aggregation for the facilitator dashboard."""

from backend.services.evaluation_result_service import EvaluationResultService


def assessment_is_assigned_to_facilitator(assessment, facilitator_id):
    """Return whether the assessment's current or legacy assignment includes the facilitator."""
    if not facilitator_id:
        return False
    facilitator_ids = assessment.get("facilitator_ids")
    if not facilitator_ids:
        facilitator_ids = [assessment.get("facilitator_id", "")]
    elif isinstance(facilitator_ids, str):
        facilitator_ids = [facilitator_ids]
    elif not isinstance(facilitator_ids, (list, tuple, set)):
        facilitator_ids = []
    return facilitator_id in facilitator_ids


class FacilitatorDashboardService:
    def __init__(
        self,
        evaluation_results=None,
        response_repository=None,
        assignment_repository=None,
        legacy_response_loader=None,
        facilitator_repository=None,
    ):
        self.evaluation_results = evaluation_results or EvaluationResultService()
        self.response_repository = response_repository or self.evaluation_results.response_repository
        self.assignment_repository = assignment_repository or self.evaluation_results.assignment_repository
        self.legacy_response_loader = legacy_response_loader or self._legacy_response
        self.facilitator_repository = facilitator_repository

    @staticmethod
    def _legacy_response(candidate_id, assessment_name, test_name):
        from ai_hybrid_evaluator.services.candidate_response_service import get_latest_candidate_response

        return get_latest_candidate_response(
            candidate_id=candidate_id,
            assessment_name=assessment_name,
            test_name=test_name,
            require_assessment_scope=True,
        )

    @staticmethod
    def filter_overview(rows, query):
        normalized_query = str(query or "").strip().casefold()
        if not normalized_query:
            return rows
        return [
            row for row in rows
            if normalized_query in str(row.get("assessment_name", "")).casefold()
        ]

    @staticmethod
    def _identity(record, assessment_id, assessment_name, test_id, test_name):
        if record.get("assessment_id"):
            assessment_matches = record["assessment_id"] == assessment_id
        else:
            assessment_matches = record.get("assessment_name") == assessment_name
        if record.get("test_id"):
            test_matches = record["test_id"] == test_id
        else:
            test_matches = record.get("test_name") == test_name
        return assessment_matches and test_matches

    def _facilitator_names(self):
        repository = self.facilitator_repository
        if repository is None:
            catalog = getattr(self.evaluation_results, "assessments", None)
            store = getattr(catalog, "repository", None)
            if store is not None and getattr(store, "file_path", None) is not None:
                from pathlib import Path
                from backend.data_paths import resolve_data_path
                from backend.repositories.facilitator_repository import FacilitatorRepository
                path = Path(store.file_path).parent / "facilitators.json"
                # Dashboard reads must never initialize a missing directory/store.
                if resolve_data_path(path).exists():
                    repository = FacilitatorRepository(path)
        rows = repository.get_all() if repository is not None else []
        return {str(row["emp_id"]): str(row["name"]) for row in rows}

    @staticmethod
    def collaboration_activity(assessment, overview):
        stats = {row["test_name"]: row for row in (overview or {}).get("test_stats", [])}
        activity = []
        names = assessment.get("all_tests")
        if not isinstance(names, list):
            names = list(assessment.get("tests") or [])
            if assessment.get("final_test"):
                names.append(assessment["final_test"])
        for index, name in enumerate(dict.fromkeys(names), 1):
            row = stats.get(name, {})
            completed = row.get("eval_completed", 0)
            pending = row.get("pending_eval", 0)
            if completed > 0 and pending == 0:
                status, color = "Completed", "green"
            elif completed > 0 or pending > 0 or row.get("completed", 0) > 0:
                status, color = "In Progress", "orange"
            else:
                status, color = "Not Started", "gray"
            locked = row.get("is_locked", False)
            actors = list(row.get("evaluators", []))
            if row.get("unattributed_evaluations") and "Not recorded" not in actors:
                actors.append("Not recorded")
            activity.append({"index": str(index), "test_name": name,
                "evaluation_status": status, "status_color": color,
                "evaluated_by": ", ".join(actors) or ("Not recorded" if completed else "-"),
                "lock_status": "Locked" if locked else "Unlocked",
                "locked_by": (row.get("locked_by", "") or "Not recorded") if locked else "-"})
        return activity

    def get_assessments_overview(self, assessments):
        responses = self.response_repository.get_all()
        assignments = self.assignment_repository.get_all()
        evaluations = self.evaluation_results.list_results()
        facilitator_names = self._facilitator_names()
        response_map = {
            (record["candidate_id"], record["assessment_id"], record["test_id"]): record
            for record in responses
        }
        assignment_map = {
            (record["candidate_id"], record["assessment_id"], record["test_id"]): record
            for record in assignments
        }
        result = []

        for assessment in assessments:
            assessment_id = assessment.get("assessment_id", "")
            assessment_name = assessment.get("name", "")
            candidates = list(dict.fromkeys(
                candidate_id.strip()
                for candidate_id in (assessment.get("assigned_candidates") or [])
                if isinstance(candidate_id, str) and candidate_id.strip()
            ))
            test_names = assessment.get("all_tests")
            if not isinstance(test_names, list):
                test_names = list(assessment.get("tests") or [])
                final_test = assessment.get("final_test", "")
                if final_test:
                    test_names.append(final_test)
            test_names = list(dict.fromkeys(
                test_name.strip()
                for test_name in test_names
                if isinstance(test_name, str) and test_name.strip()
            ))
            test_ids = assessment.get("test_ids") or {}
            if not isinstance(test_ids, dict):
                test_ids = {}
            catalog = getattr(self.evaluation_results, "assessments", None)
            canonical_tests = catalog.list_tests(assessment_id) if assessment_id and catalog is not None else []
            lock_states = assessment.get("test_lock_states") or {}
            lock_states = dict(lock_states) if isinstance(lock_states, dict) else {}
            if assessment_id and catalog is not None:
                for test in canonical_tests:
                    lock_states[test["test_name"]] = test
                    if test.get("test_name") and test.get("test_id"):
                        test_ids = {**test_ids, test["test_name"]: test["test_id"]}
            tests = [
                {"test_name": name, "test_id": test_ids.get(name, "")}
                for name in test_names
            ]

            test_stats = {
                test["test_name"]: {
                    "test_name": test["test_name"],
                    "completed": 0,
                    "not_completed": 0,
                    "eval_completed": 0,
                    "pending_eval": 0,
                    "evaluators": [],
                    "unattributed_evaluations": 0,
                    "is_locked": bool(lock_states.get(test["test_name"], {}).get("is_locked", False)),
                    "locked_by": facilitator_names.get(
                        str(lock_states.get(test["test_name"], {}).get("locked_by") or ""),
                        str(lock_states.get(test["test_name"], {}).get("locked_by") or "")),
                }
                for test in tests
            }
            submitted_pairs = set()
            evaluated_pairs = set()
            evaluator_names = {}

            for evaluation in evaluations:
                if evaluation.get("evaluation_status") != "completed":
                    continue
                candidate_id = str(evaluation.get("candidate_id", ""))
                test_name = evaluation.get("test_name", "")
                test_id = evaluation.get("test_id", "")
                if candidate_id and test_name in test_stats and self._identity(
                    evaluation, assessment_id, assessment_name, test_ids.get(test_name, ""), test_name
                ):
                    pair = (candidate_id, test_name)
                    evaluated_pairs.add(pair)
                    evaluator = evaluation.get("evaluated_by_id") or evaluation.get("evaluated_by")
                    if isinstance(evaluator, str) and evaluator.strip():
                        actor = str(evaluator).strip()
                        evaluator_names.setdefault(pair, set()).add(facilitator_names.get(actor, actor))

            for candidate_id in candidates:
                for test in tests:
                    test_name = test["test_name"]
                    test_id = test["test_id"]
                    identity = (candidate_id, assessment_id, test_id)
                    response = response_map.get(identity)
                    assignment = assignment_map.get(identity)

                    if response is not None:
                        submitted = (
                            response.get("status") == "Submitted"
                            and not response.get("_pending_status")
                            and (assignment is None or assignment.get("status") == "Submitted")
                        )
                    elif assignment is not None:
                        submitted = assignment.get("status") == "Submitted"
                    else:
                        legacy = self.legacy_response_loader(
                            candidate_id, assessment_name, test_name
                        )
                        submitted = bool(legacy.get("responses")) if isinstance(legacy, dict) else False

                    pair = (candidate_id, test_name)
                    if submitted:
                        submitted_pairs.add(pair)
                        test_stats[test_name]["completed"] += 1
                        if pair in evaluated_pairs:
                            test_stats[test_name]["eval_completed"] += 1
                            if not evaluator_names.get(pair):
                                test_stats[test_name]["unattributed_evaluations"] += 1
                            test_stats[test_name]["evaluators"].extend(
                                sorted(evaluator_names.get(pair, set()))
                            )
                        else:
                            test_stats[test_name]["pending_eval"] += 1
                    else:
                        test_stats[test_name]["not_completed"] += 1

            for stats in test_stats.values():
                stats["evaluators"] = list(dict.fromkeys(stats["evaluators"]))

            total_candidate_tests = len(candidates) * len(tests)
            submitted_count = len(submitted_pairs)
            evaluated_count = len(evaluated_pairs & submitted_pairs)
            result.append({
                "assessment_id": assessment_id,
                "assessment_name": assessment_name,
                "total_tests": len(tests),
                "candidate_tests_completed": submitted_count,
                "not_completed": total_candidate_tests - submitted_count,
                "pending_evaluations": submitted_count - evaluated_count,
                "evaluations_completed": evaluated_count,
                "total_candidate_tests": total_candidate_tests,
                "test_stats": list(test_stats.values()),
            })

        return result
