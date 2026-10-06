"""Persisted question-wise LLM evaluation for objective, subjective and mixed papers."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from threading import RLock
from uuid import uuid4
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository

_LOCK = RLock()
_PROCESS = uuid4().hex
_ACTIVE = set()
_TRANSITIONS = {
    'idle': {'running', 'restarting'}, 'running': {'stop_requested', 'completed', 'failed', 'restarting'},
    'stop_requested': {'paused', 'restarting'}, 'paused': {'running', 'restarting'},
    'failed': {'restarting'}, 'completed': {'restarting'}, 'restarting': {'running', 'abandoned'},
    'abandoned': set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


class AIEvaluationRunService:
    def __init__(self, repository=None, tests=None):
        self.repository = repository or AIEvaluationRunRepository()
        from backend.services.test_service import TestService
        from backend.repositories.test_repository import TestRepository
        self.tests = tests or (TestService(TestRepository(self.repository.file_path.parent / 'tests.json'))
                               if repository is not None else TestService())

    def _canonical_test(self, run):
        if not run.get('test_id') or not run.get('assessment_id'):
            raise ValueError('Canonical assessment/test IDs are required; start a new evaluation from the assigned test.')
        test = self.tests.get_test(run['test_id'], run['assessment_id'])
        if test.get('test_type') not in ('objective', 'subjective', 'mixed'):
            raise ValueError(
                'Test type is missing or unknown; upload the question paper again before evaluation.'
            )
        return test

    def _validate_submission_snapshot(self, run, test):
        from backend.services.question_paper_service import QuestionPaperService
        from backend.repositories.response_repository import ResponseRepository
        paper = QuestionPaperService(self.tests).get_paper(test['assessment_id'], test['test_id'])
        if not paper:
            raise ValueError('A validated canonical question paper is required; upload it again.')
        def number(value):
            return str(int(float(str(value).strip().removeprefix('Q'))))
        questions = {number(q['Question No']): q for q in paper['questions']}
        responses = ResponseRepository(self.tests.repository.file_path.parent / 'responses.json')
        keyed = {}
        for cid in run['candidate_ids']:
            response = responses.get(cid, test['assessment_id'], test['test_id'])
            if not response or response['status'] != 'Submitted' or response.get('_pending_status'):
                raise ValueError(f'{cid}: a finalized submission for this assessment/test is required.')
            rows = [q['record'] for q in run['questions'] if q['record']['candidate_id'] == cid]
            if len(rows) != len(questions) or {number(r['question_no']) for r in rows} != set(questions):
                raise ValueError(f'{cid}: response must contain every question from this test exactly once.')
            for row in rows:
                n = number(row['question_no'])
                question = questions[n]
                answer = response['answers'].get(n, '').strip()
                if (row['question'].strip() != question['Question'].strip()
                        or row['max_marks'] != question['Marks']
                        or str(row['candidate_answer'] or '').strip() != answer
                        or row['unanswered'] != (not answer)):
                    raise ValueError(f'{cid} Q{n}: evaluation input differs from the canonical paper/submission.')
                keyed[str(row['question_no'])] = question
        return keyed

    def _save(self, run, persist=True):
        states = [q['status'] for q in run['questions']]
        run['total_questions'] = len(states)  # candidate/question pairs for a cohort
        run['completed_questions'] = states.count('completed')
        run['failed_questions'] = states.count('failed')
        run['pending_questions'] = states.count('pending') + states.count('evaluating')
        run['percentage'] = 100 * run['completed_questions'] / len(states) if states else 0
        run['updated_at'] = _now()
        return self.repository.save(run) if persist else run

    def create_run(self, assessment_name, test_name, records, *, candidate_scope='single', labels=None,
                   assessment_id='', test_id='', skipped=None, restarted_from_run_id=None, _persist=True):
        if not assessment_name or not test_name or not records:
            raise ValueError('Assessment, test and actual question records are required.')
        if candidate_scope not in ('single', 'all'):
            raise ValueError('Invalid candidate scope.')
        records = deepcopy(records)
        pairs = set()
        for record in records:
            candidate = record.get('candidate_id')
            number = str(record.get('question_no', '')).strip()
            if not isinstance(candidate, str) or not candidate or not number:
                raise ValueError('Stable candidate ID and question number are required.')
            if (candidate, number) in pairs:
                raise ValueError('Duplicate candidate/question pair.')
            maximum = record.get('max_marks')
            if isinstance(maximum, bool) or not isinstance(maximum, (int, float)) or not math.isfinite(maximum) or maximum < 0:
                raise ValueError('Invalid question maximum marks.')
            if not isinstance(record.get('metadata'), dict) or not isinstance(record.get('unanswered'), bool):
                raise ValueError('Question records must be normalized by the AI engine.')
            pairs.add((candidate, number))
            for field, expected in (('assessment_name', assessment_name), ('test_name', test_name)):
                if record.get(field, expected) != expected:
                    raise ValueError('Question belongs to a different assessment/test.')
            record['question_no'] = number
            record['assessment_name'] = assessment_name
            record['test_name'] = test_name
        candidates = list(dict.fromkeys(r['candidate_id'] for r in records))
        if candidate_scope == 'single' and len(candidates) != 1:
            raise ValueError('Single-candidate run must contain exactly one candidate.')
        # JSON snapshots keep Resume independent of later workbook/selector changes.
        records = json.loads(json.dumps(records, allow_nan=False))
        with _LOCK:
            for old in self.repository.get_all():
                same_scope = ((old.get('assessment_id'), old.get('test_id')) == (assessment_id, test_id)
                              if old.get('assessment_id') and old.get('test_id') and assessment_id and test_id
                              else (old['assessment_name'], old['test_name']) == (assessment_name, test_name))
                if same_scope:
                    if old['status'] in ('idle', 'running', 'stop_requested', 'paused', 'restarting') and set(old['candidate_ids']) & set(candidates):
                        if old['run_id'] != restarted_from_run_id:
                            raise ValueError('An unfinished run already exists for this candidate/assessment/test; resume or restart it.')
            now = _now()
            return self._save({'run_id': uuid4().hex, 'candidate_ids': candidates,
                'candidate_id': candidates[0] if candidate_scope == 'single' else None,
                'candidate_scope': candidate_scope, 'candidate_labels': labels or {},
                'assessment_name': assessment_name, 'test_name': test_name,
                'assessment_id': assessment_id, 'test_id': test_id, 'evaluation_type': 'ai',
                'status': 'restarting' if restarted_from_run_id else 'idle',
                'questions': [{'pair_id': uuid4().hex, 'record': r, 'status': 'pending', 'result': None, 'error': ''} for r in records],
                'current_question': None, 'created_at': now, 'updated_at': now,
                'stop_requested': False, 'restarted_from_run_id': restarted_from_run_id,
                'superseded_by_run_id': None, 'execution_token': None, 'owner_process': None, 'owner_pid': None,
                'skipped': skipped or [], 'error': ''}, persist=_persist)

    def get_run(self, run_id):
        with _LOCK:
            return self.repository.get(run_id)

    def find_run(self, assessment, test, candidate_ids, candidate_scope):
        with _LOCK:
            matches = [r for r in self.repository.get_all() if r['assessment_name'] == assessment
                       and r['test_name'] == test and (candidate_ids is None or set(r['candidate_ids']) == set(candidate_ids))
                       and r['candidate_scope'] == candidate_scope and not r.get('superseded_by_run_id')]
            return max(matches, key=lambda r: r['created_at']) if matches else None

    @staticmethod
    def _transition(run, status):
        if status not in _TRANSITIONS.get(run['status'], set()):
            raise ValueError(f"Invalid evaluation transition: {run['status']} -> {status}")
        run['status'] = status

    def request_stop(self, run_id):
        with _LOCK:
            run = self.repository.get(run_id)
            if run['status'] != 'stop_requested':
                self._transition(run, 'stop_requested')
            run['stop_requested'] = True
            return self._save(run)

    @staticmethod
    def _owner_alive(pid):
        if not pid:
            return True  # Unknown ownership must not authorize taking over a worker.
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                return ctypes.get_last_error() != 87
            try:
                code = wintypes.DWORD()
                return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
            finally:
                kernel.CloseHandle(handle)
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def recover_interrupted(self, run_id):
        """Explicit recovery after a process restart; never steal a live worker."""
        with _LOCK:
            run = self.repository.get(run_id)
            if run['status'] in ('running', 'stop_requested') and run['owner_process'] != _PROCESS and not self._owner_alive(run.get('owner_pid')):
                run['status'] = 'paused'
                run['execution_token'] = None
                run['error'] = 'Previous process ended. Uncheckpointed work is pending.'
                for q in run['questions']:
                    if q['status'] == 'evaluating':
                        q['status'] = 'pending'
                run['current_question'] = None
                return self._save(run)
            return run

    def restart(self, run_id):
        with _LOCK:
            old = self.repository.get(run_id)
            if old.get('superseded_by_run_id'):
                raise ValueError('This run has already been restarted.')
            self._transition(old, 'restarting')
            old['stop_requested'] = True
            new = self.create_run(old['assessment_name'], old['test_name'], [q['record'] for q in old['questions']],
                candidate_scope=old['candidate_scope'], labels=old['candidate_labels'],
                assessment_id=old['assessment_id'], test_id=old['test_id'], skipped=old['skipped'], restarted_from_run_id=run_id, _persist=False)
            old['superseded_by_run_id'] = new['run_id']
            self._transition(old, 'abandoned')
            self.repository.save_many([self._save(old, persist=False), new])
            return new

    def start(self, run_id):
        with _LOCK:
            run = self.repository.get(run_id)
            if run.get('superseded_by_run_id'):
                raise ValueError('Cannot start a superseded run.')
            self._transition(run, 'running')
            run['stop_requested'] = False
            run['execution_token'] = uuid4().hex
            run['owner_process'] = _PROCESS
            run['owner_pid'] = os.getpid()
            run['error'] = ''
            return self._save(run)

    def _next_chunk(self, run_id, token, batch_size):
        with _LOCK:
            run = self.repository.get(run_id)
            if run['execution_token'] != token or run['status'] != 'running' or run['stop_requested']:
                return []
            pending = [q for q in run['questions'] if q['status'] == 'pending']
            if not pending:
                return []

            def question_number(item):
                value = str(item['record']['question_no']).strip()
                normalized = value.removeprefix('Q').removeprefix('q').strip()
                try:
                    return int(float(normalized))
                except (TypeError, ValueError):
                    return float('inf')

            question = min(
                pending,
                key=question_number,
            )['record']['question_no']

            chunk = [
                q for q in pending
                if question_number(q) == question_number(
                    {'record': {'question_no': question}}
                )
            ][:batch_size]
            for q in chunk:
                q['status'] = 'evaluating'
            run['current_question'] = question
            self._save(run)
            return deepcopy(chunk)

    def checkpoint(self, run_id, token, pair_id, result=None, error=''):
        with _LOCK:
            run = self.repository.get(run_id)
            if token != run['execution_token']:
                raise ValueError('Stale evaluation worker token.')
            q = next((q for q in run['questions'] if q['pair_id'] == pair_id), None)
            if q is None or q['status'] != 'evaluating':
                raise ValueError('Question is not evaluating in this run.')
            if result is not None:
                marks = result.get('awarded_marks')
                maximum = q['record']['max_marks']
                if isinstance(marks, bool) or not isinstance(marks, (float, int)) or not math.isfinite(marks) or not 0 <= marks <= maximum:
                    raise ValueError('Invalid marks from evaluation engine.')
                mode = q['record'].get('question_type') or self._canonical_test(run)['test_type']
                if mode not in ('objective', 'subjective'):
                    raise ValueError('Missing canonical per-question grading mode.')
                if mode == 'objective' and marks not in (0, maximum):
                    raise ValueError('Objective marks must be zero or full marks.')
                result = deepcopy(result)
                result.update(assessment_id=run['assessment_id'], test_id=run['test_id'],
                              response_id=pair_id, question_type=mode, test_type=mode)
                result.update({k: q['record'][k] for k in ('candidate_id', 'question_no', 'question', 'candidate_answer', 'unanswered', 'assessment_name', 'test_name')})
                result.update(q['record']['metadata'])
                result['maximum_marks'] = maximum
                result['percentage'] = 100 * marks / maximum if maximum else 0
                result['status'] = 'unanswered' if q['record']['unanswered'] else 'completed'
                q.update(status='completed', result=result, error='')
            else:
                q.update(status='failed', result=None, error=error or 'Evaluation failed.')
            return self._save(run)

    def finish(self, run_id, token, error=''):
        with _LOCK:
            run = self.repository.get(run_id)
            if run['execution_token'] != token:
                return run
            for q in run['questions']:
                if q['status'] == 'evaluating':
                    q['status'] = 'pending'
            if run['status'] == 'stop_requested':
                self._transition(run, 'paused')
            elif run['status'] == 'running':
                status = 'completed' if all(q['status'] == 'completed' for q in run['questions']) and not error else 'failed'
                self._transition(run, status)
            run['current_question'] = None
            run['error'] = error
            return self._save(run)

    def _attach_canonical_question_types(self, rows, test_record):
        """
        Attach and verify the authoritative per-question grading mode.

        The validated canonical Question Paper stored in the JSON repository
        is authoritative. Workbook-derived question_type values are never
        trusted for evaluation routing.
        """
        from backend.services.question_paper_service import QuestionPaperService

        paper = QuestionPaperService(self.tests).get_paper(
            test_record['assessment_id'],
            test_record['test_id'],
        )

        if not paper:
            raise ValueError(
                'A validated canonical question paper is required before evaluation.'
            )

        def number(value):
            return str(
                int(
                    float(
                        str(value).strip().removeprefix('Q')
                    )
                )
            )

        canonical = {}

        for question in paper['questions']:
            qno = number(question['Question No'])

            question_type = str(
                question.get('question_type', '')
            ).strip().lower()

            # Legacy/pure papers may not yet carry question_type on every
            # stored question. Their canonical test type is sufficient.
            if not question_type and paper.get('test_type') in (
                'objective',
                'subjective',
            ):
                question_type = paper['test_type']

            if question_type not in ('objective', 'subjective'):
                raise ValueError(
                    f'Question Q{qno}: canonical question_type is missing '
                    f'or invalid; upload the question paper again.'
                )

            canonical[qno] = {
                'question_type': question_type,
                'question': str(question['Question']).strip(),
                'max_marks': question['Marks'],
                'answer_key': question['Answer Key'],
            }

        if len(canonical) != len(paper['questions']):
            raise ValueError(
                'Canonical question paper contains duplicate question numbers.'
            )

        for row in rows:
            qno = number(row['question_no'])
            question = canonical.get(qno)

            if question is None:
                raise ValueError(
                    f'Question Q{qno} is not present in the canonical question paper.'
                )

            if str(row['question']).strip() != question['question']:
                raise ValueError(
                    f'Question Q{qno}: evaluation question differs from '
                    f'the canonical question paper.'
                )

            if row['max_marks'] != question['max_marks']:
                raise ValueError(
                    f'Question Q{qno}: evaluation marks differ from '
                    f'the canonical question paper.'
                )

            # Canonical JSON is authoritative for both grading mode
            # and Answer Key.
            row['question_type'] = question['question_type']
            row['answer_key'] = question['answer_key']

        candidates = {r['candidate_id'] for r in rows if r.get('candidate_id')}
        for cid in candidates or {None}:
            selected = [r for r in rows if cid is None or r.get('candidate_id') == cid]
            if len(selected) != len(canonical) or {number(r['question_no']) for r in selected} != set(canonical):
                raise ValueError('Response must contain every question from this test exactly once.')
        return rows

    def prepare_single(self, assessment, test, candidate_id, label, paper, response, answer_key=None, **ids):
        from ai_hybrid_evaluator.services import ai_evaluation_service as engine

        test_record = self._canonical_test(ids)

        # Canonical paper owns the Answer Key for every paper type:
        # Objective, Subjective and Mixed.
        answer_key = None

        # Preserve the existing candidate/assessment/test response ownership
        # protection for Objective and Mixed papers.
        if test_record['test_type'] in ('objective', 'mixed'):
            from pathlib import Path
            from backend.repositories.response_repository import ResponseRepository

            stored = ResponseRepository(
                self.tests.repository.file_path.parent / 'responses.json'
            ).get(
                candidate_id,
                ids['assessment_id'],
                ids['test_id'],
            )

            if (
                not stored
                or Path(stored.get('response_file') or '').resolve()
                != Path(response).resolve()
            ):
                raise ValueError(
                    'Response workbook does not belong to this '
                    'candidate/assessment/test.'
                )

        rows = engine.prepare_candidate_records(
            paper,
            response,
            answer_key,
        )

        rows = self._attach_canonical_question_types(
            rows,
            test_record,
        )

        for row in rows:
            row['candidate_id'] = candidate_id

        return self.create_run(
            assessment,
            test,
            self._json_records(rows),
            labels={candidate_id: label},
            **ids,
        )

    def prepare_batch(self, assessment, test, rows, labels, paper, answer_key=None, skipped=None, **ids):
        from ai_hybrid_evaluator.services import ai_evaluation_service as engine

        test_record = self._canonical_test(ids)

        # Canonical JSON paper owns all Answer Keys.
        answer_key = None

        groups = engine.prepare_questionwise_records(
            paper,
            rows,
            answer_key,
        )

        normalized = [
            row
            for group in groups.values()
            for row in group
        ]

        normalized = self._attach_canonical_question_types(
            normalized,
            test_record,
        )

        return self.create_run(
            assessment,
            test,
            self._json_records(normalized),
            candidate_scope='all',
            labels=labels,
            skipped=skipped,
            **ids,
        )

    @staticmethod
    def _json_records(rows):
        # Pandas workbook scalars/empty metadata must be ordinary JSON, never NaN.
        def clean(value):
            if isinstance(value, dict):
                return {k: clean(v) for k, v in value.items()}
            if isinstance(value, list):
                return [clean(v) for v in value]
            if hasattr(value, 'item'):
                value = value.item()
            if isinstance(value, float) and not math.isfinite(value):
                return ''
            return value
        return clean(rows)

    def execute(self, run_id, *, max_retries=3, batch_size=5, delay_seconds=2):
        """One worker per run. No Azure request is forcibly cancelled."""
        worker_key = (str(self.repository.file_path.resolve()), run_id)
        with _LOCK:
            if worker_key in _ACTIVE:
                raise ValueError('Evaluation run already has a worker.')
            run = self.start(run_id)
            token = run['execution_token']
            _ACTIVE.add(worker_key)
        client = deployment = None
        fatal = ''
        try:
            test = self._canonical_test(run)
            if test['test_type'] in ('objective', 'mixed') or run.get('canonical_input'):
                self._validate_submission_snapshot(run, test)

            # Business rule:
            # Both Objective and Subjective tests are evaluated by the LLM.
            # The canonical Answer Key remains the grading reference for both.
            from ai_hybrid_evaluator.services import ai_evaluation_service as engine

            while True:
                chunk = self._next_chunk(run_id, token, batch_size if run['candidate_scope'] == 'all' else 1)
                if not chunk:
                    break
                # Resolve grading mode per question.
                #
                # Pure Objective/Subjective papers use the canonical test type.
                # Mixed papers use each question's authoritative question_type.
                # This keeps evaluation question-wise while allowing Objective
                # and Subjective questions to coexist in the same assessment.
                rows = []

                for q in chunk:
                    record = q['record']

                    grading_type = record.get('question_type') or test['test_type']

                    if grading_type not in ('objective', 'subjective'):
                        raise ValueError(
                            f"Question {record.get('question_no')}: "
                            f"missing or invalid question_type "
                            f"{grading_type!r}."
                        )

                    rows.append(
                        dict(
                            record,
                            response_id=q['pair_id'],
                            test_type=grading_type,
                        )
                    )
                try:
                    # Unanswered responses need no Azure call; the engine
                    # deterministically awards zero for them.
                    if client is None and any(not r['unanswered'] for r in rows):
                        client, deployment = engine._load_client()

                    # Both Objective and Subjective answers use the same LLM
                    # evaluation engine and their canonical Answer Key.
                    if run['candidate_scope'] == 'all':
                        outcomes = engine._evaluate_question_batch(
                            client,
                            deployment,
                            rows,
                            max_retries,
                            delay_seconds,
                            lambda pair_id, outcome: self.checkpoint(
                                run_id,
                                token,
                                pair_id,
                                result=outcome,
                            ),
                        )
                    else:
                        outcomes = [
                            engine._evaluate_with_retry(
                                client,
                                deployment,
                                rows[0],
                                max_retries,
                                delay_seconds,
                            )
                        ]
                except Exception as exc:
                    outcomes = [{'status': 'failed', 'error': str(exc)} for _ in rows]
                for q, outcome in zip(chunk, outcomes):
                    current = next(item for item in self.get_run(run_id)['questions'] if item['pair_id'] == q['pair_id'])
                    if current['status'] == 'completed':
                        continue  # Batch callback already persisted this validated result.
                    if outcome.get('status') == 'failed':
                        self.checkpoint(run_id, token, q['pair_id'], error=outcome.get('error', 'Evaluation failed'))
                    else:
                        try:
                            self.checkpoint(run_id, token, q['pair_id'], result=outcome)
                        except ValueError as exc:
                            self.checkpoint(run_id, token, q['pair_id'], error=str(exc))
        except Exception as exc:
            fatal = str(exc)
        finally:
            try:
                final = self.finish(run_id, token, fatal)
            finally:
                with _LOCK:
                    _ACTIVE.discard(worker_key)
        return final

    @staticmethod
    def result_rows(run):
        grouped = {}
        for question in run['questions']:
            record = question['record']
            row = question['result']
            if row is None:
                row = {**record, **record['metadata'], 'maximum_marks': record['max_marks'],
                       'awarded_marks': None, 'percentage': None, 'status': question['status'],
                       'error': question['error'] or 'Evaluation pending.'}
            grouped.setdefault(record['candidate_id'], []).append(row)
        return grouped
