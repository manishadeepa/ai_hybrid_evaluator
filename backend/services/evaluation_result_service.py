"""Read-only views over manual grades and completed AI run checkpoints.

No result store or evaluator is created. Manual wins by default; an explicit type
filter selects that source. Known non-submitted responses (including disqualified
and pending transitions) are withheld, never converted into zero-score results.
Legacy evaluations without response sessions remain readable. Name-only sources
must resolve uniquely and exactly against today's catalog; renames need migration
by their owning module, never fuzzy matching here.
"""
from copy import deepcopy
from datetime import datetime, timezone
import math
from pathlib import Path

from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository
from backend.repositories.response_repository import ResponseRepository
from backend.repositories.test_candidate_repository import TestCandidateRepository
from backend.services.assessment_service import AssessmentService, _PERSISTENCE_LOCK
from backend.services.ai_evaluation_run_service import _LOCK as _AI_LOCK
from backend.services.candidate_management_service import CandidateManagementService


class EvaluationResultService:
    def __init__(self, *, candidates=None, assessments=None, manual_repository=None,
                 ai_repository=None, response_repository=None, assignment_repository=None):
        self.candidates = candidates
        self.assessments = assessments or (candidates.assessments if candidates else AssessmentService())
        data = self.assessments.repository.file_path.parent
        if manual_repository is None and data.resolve() != (Path(__file__).resolve().parents[1] / 'data').resolve():
            raise ValueError('Inject a manual repository when using a custom catalog data directory.')
        self.manual_repository = manual_repository
        self.ai_repository = ai_repository or AIEvaluationRunRepository(data / 'ai_evaluation_runs.json')
        self.response_repository = response_repository or ResponseRepository(data / 'responses.json')
        self.assignment_repository = assignment_repository or TestCandidateRepository(data / 'test_candidates.json')

    @staticmethod
    def _read(repository):
        # Some existing repositories create missing files on read. Avoid that here.
        path = getattr(repository, 'file_path', None)
        if path is not None and not Path(path).exists():
            return []
        return repository.get_all()

    def _manual_rows(self):
        if self.manual_repository is not None:
            return self.manual_repository.get_all()
        path = Path(__file__).resolve().parents[1] / 'data' / 'manual_evaluations.json'
        return ManualEvaluationRepository().get_all() if path.exists() else []

    def _candidate_rows(self):
        if self.candidates is not None:
            return self.candidates.list_candidates()
        path = Path(__file__).resolve().parents[1] / 'data' / 'candidates.json'
        if path.exists():
            return CandidateManagementService().list_candidates()
        return CandidateManagementService._shared_candidates()

    @staticmethod
    def _type(value):
        if value not in (None, 'ai', 'manual'):
            raise ValueError('Evaluation type must be ai or manual.')

    def get_result(self, candidate_id, assessment_id, test_id, *, evaluation_type=None):
        """Return the authoritative final result, or None if none is eligible.

        Invalid/unknown IDs or an assessment/test mismatch raise ValueError.
        evaluation_type='ai' explicitly bypasses the manual-first display policy.
        """
        for value in (candidate_id, assessment_id, test_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Candidate, assessment and test IDs are required.')
        rows = self.list_results(candidate_id=candidate_id, assessment_id=assessment_id,
                                 test_id=test_id, evaluation_type=evaluation_type)
        return rows[0] if rows else None

    @staticmethod
    def _scope(source, assessments, tests):
        # An explicit ID must match; never fall back from an unknown ID to a name.
        matches = [a for a in assessments if
                   (a['assessment_id'] == source['assessment_id'] if source.get('assessment_id')
                    else a['name'] == source.get('assessment_name'))]
        if len(matches) != 1:
            return None
        assessment = matches[0]
        matches = [t for t in tests if t['assessment_id'] == assessment['assessment_id'] and
                   (t['test_id'] == source['test_id'] if source.get('test_id')
                    else t['test_name'] == source.get('test_name'))]
        return (assessment, matches[0]) if len(matches) == 1 else None

    @staticmethod
    def _timestamp(source):
        for field in ('completed_at', 'evaluated_at', 'updated_at', 'created_at'):
            value = source.get(field)
            if not isinstance(value, str) or not value:
                continue
            try:
                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                continue
            # Old manual timestamps lack a timezone. UTC gives stable ordering
            # without depending on the machine running this read-only adapter.
            return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc), value
        return datetime.min.replace(tzinfo=timezone.utc), ''

    @staticmethod
    def _number(value):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError('Stored evaluation marks must be finite numbers.')
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise ValueError('Stored evaluation marks must be finite numbers.') from None
        if not math.isfinite(number):
            raise ValueError('Stored evaluation marks must be finite numbers.')
        return number

    @classmethod
    def _question(cls, row, kind):
        if not isinstance(row, dict):
            raise ValueError('Invalid stored evaluation question.')
        manual = kind == 'manual'
        awarded = cls._number(row.get('marks_obtained') if manual else row.get('awarded_marks'))
        maximum = cls._number(row.get('max_marks') if manual else row.get('maximum_marks'))
        if not 0 <= awarded <= maximum:
            raise ValueError('Stored question marks are outside their maximum.')
        number = row.get('q_no') if manual else row.get('question_no')
        if number is None or not str(number).strip():
            raise ValueError('Stored question number is missing.')
        status = row.get('status') or 'completed'
        if status not in ('completed', 'unanswered'):
            raise ValueError('Stored question is not finalized.')
        result = dict(question_no=str(number), question=row.get('question') or '',
                      candidate_answer=row.get('candidate_response' if manual else 'candidate_answer') or '',
                      awarded_marks=awarded, maximum_marks=maximum,
                      percentage=round(100 * awarded / maximum, 2) if maximum else 0.0,
                      justification=row.get('justification') or '', status=status)
        for field, legacy in (('co', 'CO'), ('lo', 'LO'), ('knowledge_type', 'Knowledge Type'),
                              ('domain', 'Domain'), ('rbt_level', 'RBT level')):
            result[field] = row.get(field, row.get(legacy))
            if result[field] is None:
                result[field] = ''
        feedback = row.get('evaluation') if not manual else {}
        feedback = feedback if isinstance(feedback, dict) else {}
        for field in ('correctness', 'relevance', 'completeness'):
            value = feedback.get(field, row.get(field)) if not manual else ''
            result[field] = value if isinstance(value, str) else ''
        for field in ('strengths', 'missing_points', 'incorrect_points'):
            value = feedback.get(field, row.get(field)) if not manual else []
            result[field] = ([v for v in value if isinstance(v, str)] if isinstance(value, list)
                             else [value] if isinstance(value, str) and value else [])
        return result

    @classmethod
    def _result(cls, source, candidate, scope, questions, kind):
        if not isinstance(questions, list) or not questions:
            raise ValueError('Finalized evaluation must contain questions.')
        normalized = [cls._question(q, kind) for q in questions]
        numbers = [q['question_no'].strip().removeprefix('Q') for q in normalized]
        if len(numbers) != len(set(numbers)):
            raise ValueError('Duplicate stored evaluation question.')
        # Run percentage is execution progress, NOT a grade. All scores are derived
        # from persisted question marks; never combine questions across sources.
        total = round(sum(q['awarded_marks'] for q in normalized), 2)
        maximum = round(sum(q['maximum_marks'] for q in normalized), 2)
        assessment, test = scope
        return dict(candidate_id=candidate['candidate_id'], candidate_name=candidate.get('name', ''),
                    assessment_id=assessment['assessment_id'], assessment_name=assessment['name'],
                    test_id=test['test_id'], test_name=test['test_name'], evaluation_type=kind,
                    evaluation_status='completed', evaluated_at=cls._timestamp(source)[1],
                    total_marks=total, max_marks=maximum,
                    percentage=round(100 * total / maximum, 2) if maximum else 0.0,
                    questions=normalized, source_run_id=source.get('run_id') if kind == 'ai' else None)

    def list_results(self, *, candidate_id=None, assessment_id=None, test_id=None, evaluation_type=None):
        """One result per identity, manual-first unless a source filter is supplied.

        Latest valid completed AI run wins by completion timestamp then run_id.
        Manual duplicates use evaluated_at then storage order (last wins ties).
        Corrupt repositories/manual marks raise; invalid completed AI candidates
        are ineligible, allowing an older valid run to remain authoritative.
        """
        self._type(evaluation_type)
        with _PERSISTENCE_LOCK, _AI_LOCK:
            candidates = {c['candidate_id']: c for c in self._candidate_rows()}
            assessments = self._read(self.assessments.repository)
            tests = self._read(self.assessments.tests.repository)
            for value, identities in ((candidate_id, candidates),
                                      (assessment_id, {a['assessment_id'] for a in assessments}),
                                      (test_id, {t['test_id'] for t in tests})):
                if value is not None and (not isinstance(value, str) or value not in identities):
                    raise ValueError('Unknown candidate, assessment or test ID.')
            if assessment_id and test_id and not any(t['test_id'] == test_id and t['assessment_id'] == assessment_id for t in tests):
                raise ValueError('Test does not belong to this assessment.')
            responses = {(r['candidate_id'], r['assessment_id'], r['test_id']): r
                         for r in self._read(self.response_repository)}
            assignments = {(r['candidate_id'], r['test_id']): r for r in self._read(self.assignment_repository)}
            selected = {}

            def include(source, candidate, scope, questions, kind, tie):
                cid, aid, tid = candidate['candidate_id'], scope[0]['assessment_id'], scope[1]['test_id']
                if any(wanted is not None and wanted != actual for wanted, actual in
                       ((candidate_id, cid), (assessment_id, aid), (test_id, tid))):
                    return
                response = responses.get((cid, aid, tid))
                assignment = assignments.get((cid, tid))
                # Do not call ResponseLifecycleService.get_response: it can repair
                # pending writes. Retrieval must not finalize a submission itself.
                if response and (response['status'] != 'Submitted' or response.get('_pending_status')):
                    return
                if assignment and (assignment['assessment_id'] != aid or assignment['status'] != 'Submitted'):
                    return
                value = self._result(source, candidate, scope, questions, kind)
                value['response_status'] = response['status'] if response else assignment['status'] if assignment else 'unknown'
                rank = (kind == 'manual', self._timestamp(source)[0], tie)
                key = (cid, aid, tid)
                if key not in selected or rank > selected[key][0]:
                    selected[key] = (rank, value)

            if evaluation_type != 'ai':
                for index, source in enumerate(self._manual_rows()):
                    scope = self._scope(source, assessments, tests)
                    candidate = candidates.get(source.get('candidate_id'))
                    if scope and candidate and source.get('evaluation_type') == 'manual':
                        include(source, candidate, scope, source.get('questions'), 'manual', str(index).zfill(20))
            if evaluation_type != 'manual':
                for run in self._read(self.ai_repository):
                    if run['status'] != 'completed' or run.get('superseded_by_run_id') or run.get('error'):
                        continue
                    scope = self._scope(run, assessments, tests)
                    if not scope or any(q['status'] != 'completed' or q.get('error') or not isinstance(q.get('result'), dict)
                                        for q in run['questions']):
                        continue
                    grouped = {}
                    valid = True
                    for checkpoint in run['questions']:
                        record, result = checkpoint['record'], checkpoint['result']
                        cid = record.get('candidate_id')
                        if (cid not in run['candidate_ids'] or result.get('candidate_id') != cid
                                or result.get('question_no') != record.get('question_no')
                                or any(record.get(k) != run.get(k) or result.get(k) != run.get(k)
                                       for k in ('assessment_name', 'test_name'))):
                            valid = False
                            break
                        try:
                            if self._number(result.get('maximum_marks')) != self._number(record.get('max_marks')):
                                valid = False
                                break
                        except ValueError:
                            valid = False
                            break
                        grouped.setdefault(cid, []).append(result)
                    if not valid or set(grouped) != set(run['candidate_ids']):
                        continue
                    for cid, questions in grouped.items():
                        if cid not in candidates:
                            continue
                        try:
                            include(run, candidates[cid], scope, questions, 'ai', run['run_id'])
                        except ValueError:
                            continue  # Invalid marks/partial candidate data are not final results.
            return deepcopy([selected[key][1] for key in sorted(selected)])
