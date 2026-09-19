"""Read-only assessment evidence summary; does not grade, score, or mark reports complete."""
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class AssessmentProgressService:
    def __init__(self, assessments, response_loader=None, manual_loader=None):
        self.assessments = assessments
        self.response_loader = response_loader or self._responses
        self.manual_loader = manual_loader or self._manual_records

    @staticmethod
    def _responses(**identity):
        from ai_hybrid_evaluator.services.candidate_response_service import get_latest_candidate_response
        return get_latest_candidate_response(**identity, require_assessment_scope=True)

    @staticmethod
    def _manual_records():
        path = Path(__file__).resolve().parents[1] / 'data' / 'manual_evaluations.json'
        return JSONRepository(path).get_all() if path.exists() else []

    def get_progress(self, assessment_id, ai_results=None):
        assessment = self.assessments.get_assessment(assessment_id)
        tests = self.assessments.list_tests(assessment_id)
        candidates = list(dict.fromkeys(assessment.get('assigned_candidates', [])))
        name = assessment['name']
        # Legacy evaluation keys cannot prove assessment ownership; never guess.
        ai = {}
        for record in (ai_results or {}).values():
            if record.get('assessment_name') == name and record.get('candidate_id'):
                pair = (str(record['candidate_id']), record.get('test_name'))
                ai.setdefault(pair, []).append(record)
        manual = {}
        for record in self.manual_loader():
            if record.get('assessment_name') == name and record.get('candidate_id'):
                pair = (str(record['candidate_id']), record.get('test_name'))
                manual.setdefault(pair, []).append(record)
        pairs = []
        for candidate_id in candidates:
            for test in tests:
                test_name = test['test_name']
                response = self.response_loader(candidate_id=candidate_id, assessment_name=name, test_name=test_name)
                responses = response.get('responses', [])
                submitted = bool(responses)
                identity = (candidate_id, test_name)
                ai_rows = ai.get(identity, [])
                manual_rows = manual.get(identity, [])
                # The shared state store can also hold a manual result. Keep it in its own channel.
                manual_rows = manual_rows + [r for r in ai_rows if r.get('evaluation_type') == 'manual']
                ai_rows = [r for r in ai_rows if r.get('evaluation_type', 'ai') == 'ai']
                def complete(record):
                    return (record.get('status', 'completed') == 'completed'
                            and bool(record.get('questions'))
                            and len(record['questions']) == len(responses)
                            and not any(q.get('status') in ('failed', 'partial') for q in record['questions']))
                ai_done = submitted and any(complete(r) for r in ai_rows)
                manual_done = submitted and any(complete(r) for r in manual_rows)
                incomplete = any(not complete(r) for r in ai_rows + manual_rows) if submitted else False
                ambiguous = bool((ai_done or manual_done) and incomplete)
                evaluated = bool((ai_done or manual_done) and not ambiguous)
                pairs.append({'candidate_id': candidate_id, 'test_id': test['test_id'], 'test_name': test_name,
                              'submitted': submitted, 'ai_evaluated': bool(ai_done), 'manual_evaluated': bool(manual_done),
                              'evaluated': evaluated, 'incomplete': bool(incomplete), 'ambiguous': ambiguous,
                              'failed': any(r.get('status') == 'failed' for r in ai_rows + manual_rows)})
        total = len(pairs)
        submitted_pairs = sum(r['submitted'] for r in pairs)
        evaluated_pairs = sum(r['evaluated'] for r in pairs)
        ambiguous_pairs = sum(r['ambiguous'] for r in pairs)
        def all_tests(candidate_id, field):
            rows = [r for r in pairs if r['candidate_id'] == candidate_id]
            return bool(rows) and all(r[field] for r in rows)
        evaluated_candidates = sum(all_tests(c, 'evaluated') for c in candidates)
        return {'assessment_id': assessment_id, 'total_assigned_candidates': len(candidates), 'total_tests': len(tests),
                'submitted_candidates': sum(any(r['submitted'] and r['candidate_id'] == c for r in pairs) for c in candidates),
                'fully_submitted_candidates': sum(all_tests(c, 'submitted') for c in candidates),
                'evaluated_candidates': evaluated_candidates, 'pending_candidates': len(candidates) - evaluated_candidates,
                'incomplete_candidates': sum(any(r['incomplete'] and r['candidate_id'] == c for r in pairs) for c in candidates),
                'failed_candidates': sum(any(r['failed'] and r['candidate_id'] == c for r in pairs) for c in candidates),
                'total_candidate_tests': total, 'submitted_candidate_tests': submitted_pairs,
                'evaluated_candidate_tests': evaluated_pairs, 'pending_candidate_tests': total - evaluated_pairs,
                'ambiguous_candidate_tests': ambiguous_pairs,
                'progress_percentage': round(100 * evaluated_pairs / total, 1) if total and not ambiguous_pairs else (None if ambiguous_pairs else 0.0),
                'complete': None if ambiguous_pairs else bool(total and evaluated_pairs == total),
                'pairs': pairs,
                'limitations': ['AI evidence is limited to the supplied session results; unscoped legacy records are excluded.']
                    + (['Conflicting completed/incomplete evaluation evidence requires a precedence rule.'] if ambiguous_pairs else [])}
