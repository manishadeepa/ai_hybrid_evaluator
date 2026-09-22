"""Stored result facade tests: real temporary repositories, no model execution."""
from copy import deepcopy
import builtins
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.json_repository import JSONRepository
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.manual_evaluation_service import ManualEvaluationService
from backend.services.ai_evaluation_run_service import AIEvaluationRunService
from backend.services.evaluation_result_service import EvaluationResultService


class EvaluationResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidates = CandidateManagementService(CandidateRepository(self.root / 'candidates.json'))
        for cid in ('C1', 'C2'):
            self.candidates.create_candidate(dict(candidate_id=cid, name=cid + ' Name', email=cid + '@example.com'))
        self.a = self.candidates.assessments.create_assessment(dict(name='A', tests=['Formative 1', 'Formative 2']))
        self.b = self.candidates.assessments.create_assessment(dict(name='B', tests=['Formative 1']))
        self.key = ('C1', self.a['assessment_id'], self.a['test_ids']['Formative 1'])
        self.manual = object.__new__(ManualEvaluationRepository)
        self.manual.storage = JSONRepository(self.root / 'manual.json')
        self.runs = AIEvaluationRunService(AIEvaluationRunRepository(self.root / 'ai_evaluation_runs.json'))
        self.service = EvaluationResultService(candidates=self.candidates, manual_repository=self.manual,
                                               ai_repository=self.runs.repository)

    def manual_result(self, candidate='C1', assessment='A', test='Formative 1'):
        return ManualEvaluationService(self.manual).evaluate_and_save(candidate, assessment, test, [
            dict(q_no='Q1', question='Question 1', response='Answer 1', max_marks=4, awarded_marks=3,
                 justification='Manual reason', CO='CO1', LO='LO1', **{'Knowledge Type': 'Fact', 'Domain': 'Cognitive', 'RBT level': 'Remember'}),
            dict(q_no='Q2', question='Question 2', response='', max_marks=2, awarded_marks=0)])

    def ai_result(self, candidates=('C1',), complete=True, ids=True):
        rows = [dict(candidate_id=cid, question_no=f'Q{i}', question=f'Question {i}', candidate_answer='Answer' if i == 1 else '',
                     unanswered=i == 2, answer_key='Reference', max_marks=2,
                     metadata=dict(co='CO1', lo='LO1', knowledge_type='Fact', domain='Cognitive', rbt_level='Remember'))
                for cid in candidates for i in (1, 2)]
        run = self.runs.create_run('A', 'Formative 1', rows, candidate_scope='single' if len(candidates) == 1 else 'all',
                                   assessment_id=self.key[1] if ids else '', test_id=self.key[2] if ids else '')
        if not complete: return run
        run = self.runs.start(run['run_id'])
        token, rid = run['execution_token'], run['run_id']
        while chunk := self.runs._next_chunk(rid, token, 5):
            for q in chunk:
                self.runs.checkpoint(rid, token, q['pair_id'], dict(awarded_marks=0 if q['record']['unanswered'] else 1,
                    justification='Stored reason', evaluation=dict(correctness='Partial', relevance='Relevant', completeness='Partial',
                    strengths=['A point'], missing_points=['B point'], incorrect_points=[])))
        return self.runs.finish(rid, token)

    def response(self, status, pending=False):
        cid, aid, tid = self.key
        self.service.response_repository.save(dict(candidate_id=cid, candidate_name='C1 Name', assessment_id=aid, test_id=tid,
            assessment_name='A', test_name='Formative 1', status=status, answers={}, marked_for_review=[], violation_count=0,
            questions=[dict(id=1)], **({'_pending_status': status} if pending else {})))

    def test_manual_only_normalization(self):
        stored = self.manual_result()
        value = self.service.get_result(*self.key)
        self.assertEqual(value['evaluation_type'], 'manual')
        self.assertEqual(value['evaluation_status'], 'completed')
        self.assertEqual(value['candidate_name'], 'C1 Name')
        self.assertEqual(value['evaluated_at'], stored['evaluated_at'])
        self.assertEqual((value['total_marks'], value['max_marks'], value['percentage']), (3, 6, 50))
        q = value['questions'][0]
        self.assertEqual((q['question_no'], q['candidate_answer'], q['awarded_marks'], q['maximum_marks'], q['percentage']), ('Q1', 'Answer 1', 3, 4, 75))
        self.assertEqual((q['co'], q['lo'], q['knowledge_type'], q['domain'], q['rbt_level']), ('CO1', 'LO1', 'Fact', 'Cognitive', 'Remember'))
        self.assertEqual(q['correctness'], '')
        self.assertEqual(q['strengths'], [])

    def test_completed_ai_only(self):
        run = self.ai_result()
        value = self.service.get_result(*self.key)
        self.assertEqual(value['source_run_id'], run['run_id'])
        self.assertEqual(value['evaluation_type'], 'ai')
        self.assertEqual(value['evaluated_at'], run['updated_at'])
        self.assertEqual(value['questions'][0]['strengths'], ['A point'])
        self.assertEqual(value['questions'][1]['status'], 'unanswered')
        self.assertEqual((value['total_marks'], value['max_marks'], value['percentage']), (1, 4, 25))
        self.assertEqual(run['percentage'], 100)  # Progress is not the score.

    def test_manual_wins_without_mixing_sources(self):
        self.ai_result(); self.manual_result()
        value = self.service.get_result(*self.key)
        self.assertEqual(value['evaluation_type'], 'manual')
        self.assertEqual(value['max_marks'], 6)
        self.assertEqual(len(self.service.list_results()), 1)

    def test_explicit_ai_filter(self):
        self.ai_result(); self.manual_result()
        value = self.service.list_results(evaluation_type='ai')[0]
        self.assertEqual(value['evaluation_type'], 'ai')
        self.assertEqual(value['max_marks'], 4)
        self.assertEqual(self.service.get_result(*self.key, evaluation_type='ai'), value)

    def test_all_unfinished_and_abandoned_statuses_excluded(self):
        run = self.ai_result(complete=False)
        for status in ('idle', 'running', 'stop_requested', 'paused', 'failed', 'restarting', 'abandoned'):
            run['status'] = status; self.runs.repository.save(run)
            with self.subTest(status=status): self.assertIsNone(self.service.get_result(*self.key))

    def test_real_restart_excludes_superseded_completed_run(self):
        run = self.ai_result(); self.runs.restart(run['run_id'])
        self.assertIsNone(self.service.get_result(*self.key))

    def test_superseded_flag_excludes_even_completed_status(self):
        run = self.ai_result(); run['superseded_by_run_id'] = 'new'; self.runs.repository.save(run)
        self.assertIsNone(self.service.get_result(*self.key))

    def test_latest_valid_run_with_deterministic_tie_break(self):
        first = self.ai_result(); second = self.ai_result()
        first['updated_at'] = '2026-01-01T08:00:00+00:00'
        second['updated_at'] = '2026-01-01T14:00:00+05:30'
        self.runs.repository.save(first); self.runs.repository.save(second)
        self.assertEqual(self.service.get_result(*self.key)['source_run_id'], second['run_id'])
        second['updated_at'] = first['updated_at']; self.runs.repository.save(second)
        self.assertEqual(self.service.get_result(*self.key)['source_run_id'], max(first['run_id'], second['run_id']))

    def test_invalid_latest_marks_fall_back_to_valid_run(self):
        old = self.ai_result(); new = self.ai_result()
        new['questions'][0]['result']['awarded_marks'] = 999
        self.runs.repository.save(new)
        self.assertEqual(self.service.get_result(*self.key)['source_run_id'], old['run_id'])

    def test_inconsistent_completed_run_not_final(self):
        run = self.ai_result()
        run['questions'][0]['status'] = 'pending'; self.runs.repository.save(run)
        self.assertIsNone(self.service.get_result(*self.key))

    def test_batch_separates_candidates(self):
        self.ai_result(candidates=('C1', 'C2'))
        values = self.service.list_results()
        self.assertEqual([r['candidate_id'] for r in values], ['C1', 'C2'])
        self.assertEqual([len(r['questions']) for r in values], [2, 2])
        self.assertEqual(len(self.service.list_results(candidate_id='C2')), 1)

    def test_invalid_ids_and_relationship(self):
        for key in (('', self.key[1], self.key[2]), ('missing', self.key[1], self.key[2]),
                    ('C1', 'missing', self.key[2]), ('C1', self.key[1], 'missing'),
                    ('C1', self.b['assessment_id'], self.key[2])):
            with self.subTest(key=key), self.assertRaises(ValueError): self.service.get_result(*key)
        with self.assertRaises(ValueError): self.service.list_results(evaluation_type='mixed')
        self.assertIsNone(self.service.get_result(*self.key))

    def test_exact_legacy_scope_no_fuzzy_matching(self):
        self.manual_result(assessment='a')
        self.assertIsNone(self.service.get_result(*self.key))
        self.manual_result(assessment='B')
        self.assertIsNone(self.service.get_result(*self.key))
        self.assertEqual(len(self.service.list_results(assessment_id=self.b['assessment_id'])), 1)

    def test_legacy_ai_without_ids(self):
        self.ai_result(ids=False)
        self.assertEqual(self.service.get_result(*self.key)['assessment_id'], self.key[1])

    def test_explicit_wrong_ids_never_fall_back_to_names(self):
        run = self.ai_result(); run['test_id'] = 'unknown'; self.runs.repository.save(run)
        self.assertIsNone(self.service.get_result(*self.key))

    def test_stable_ids_survive_display_name_change(self):
        self.ai_result()
        self.candidates.assessments.repository.save({**self.candidates.assessments.repository.get_by_id(self.key[1]), 'name': 'Renamed'})
        self.assertEqual(self.service.get_result(*self.key)['assessment_name'], 'Renamed')

    def test_in_progress_disqualified_and_pending_are_withheld(self):
        self.manual_result(); self.ai_result()
        for status, pending in (('In Progress', False), ('Disqualified', False), ('Submitted', True)):
            self.response(status, pending)
            with self.subTest(status=status, pending=pending):
                self.assertIsNone(self.service.get_result(*self.key))
                self.assertEqual(self.service.list_results(evaluation_type='ai'), [])
        self.response('Submitted')
        self.assertEqual(self.service.get_result(*self.key)['response_status'], 'Submitted')

    def test_assignment_state_cannot_be_overridden_by_results(self):
        self.manual_result(); self.response('Submitted')
        for status in ('Assigned', 'In Progress', 'Disqualified'):
            self.service.assignment_repository.save(dict(candidate_id='C1', assessment_id=self.key[1], test_id=self.key[2], status=status))
            self.assertIsNone(self.service.get_result(*self.key))

    def test_missing_optional_feedback_safe_defaults(self):
        run = self.ai_result()
        for q in run['questions']:
            q['result']['evaluation'] = None
            q['result']['co'] = None
        self.runs.repository.save(run)
        q = self.service.get_result(*self.key)['questions'][0]
        self.assertEqual(q['correctness'], '')
        self.assertEqual(q['missing_points'], [])
        self.assertEqual(q['co'], '')

    def test_totals_derived_from_questions_zero_max_and_numeric_strings(self):
        value = self.manual_result()
        value.update(total_marks=999, max_marks=999, percentage=999)
        value['questions'][0].update(marks_obtained='1', max_marks='3')
        value['questions'][1].update(marks_obtained=0, max_marks=0)
        self.manual.save(value)
        result = self.service.get_result(*self.key)
        self.assertEqual((result['total_marks'], result['max_marks'], result['percentage']), (1, 3, 33.33))
        self.assertEqual(result['questions'][1]['percentage'], 0)

    def test_invalid_manual_marks_and_duplicate_questions_fail_closed(self):
        value = self.manual_result()
        for bad in ('NaN', -1, 100, True, None):
            changed = deepcopy(value); changed['questions'][0]['marks_obtained'] = bad
            self.manual.save(changed)
            with self.assertRaises(ValueError): self.service.get_result(*self.key)
        value['questions'].append(value['questions'][0]); self.manual.save(value)
        with self.assertRaises(ValueError): self.service.get_result(*self.key)

    def test_corrupt_json_propagates_without_repair(self):
        self.manual.storage.file_path.write_text('broken')
        with self.assertRaises(ValueError): self.service.get_result(*self.key)
        self.assertEqual(self.manual.storage.file_path.read_text(), 'broken')

    def test_no_source_mutation_or_evaluation_calls(self):
        self.manual_result(); self.ai_result(); self.response('Submitted')
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(AIEvaluationRunService, 'execute', side_effect=AssertionError('No evaluation')),
              patch.object(JSONRepository, 'save_all', side_effect=AssertionError('No writes'))):
            first = self.service.get_result(*self.key)
            self.service.list_results(evaluation_type='ai')
            first['questions'][0]['awarded_marks'] = 999
            self.assertEqual(self.service.get_result(*self.key)['total_marks'], 3)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse((self.root / 'evaluation_results.json').exists())

    def test_missing_stores_not_created_by_read(self):
        before = {p for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.service.list_results(), [])
        self.assertEqual(before, {p for p in self.root.rglob('*') if p.is_file()})

    def test_checkpoint_identity_tampering_excluded(self):
        run = self.ai_result(); run['questions'][0]['result']['candidate_id'] = 'C2'
        self.runs.repository.save(run)
        self.assertIsNone(self.service.get_result(*self.key))



    def test_modified_checkpoint_maximum_is_not_authoritative(self):
        run = self.ai_result()
        run['questions'][0]['result']['maximum_marks'] = 100
        self.runs.repository.save(run)
        self.assertIsNone(self.service.get_result(*self.key))

    def test_retrieval_does_not_import_azure_or_grading_engine(self):
        self.ai_result(); self.manual_result()
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.startswith(('openai', 'azure', 'dotenv')) or 'ai_evaluation_service' in name:
                raise AssertionError('Result retrieval must not load model/configuration code')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded):
            self.assertEqual(len(self.service.list_results(evaluation_type='ai')), 1)
            self.assertEqual(self.service.get_result(*self.key)['evaluation_type'], 'manual')

    def test_custom_catalog_requires_manual_repository_injection(self):
        with self.assertRaisesRegex(ValueError, 'Inject a manual repository'):
            EvaluationResultService(candidates=self.candidates)


if __name__ == '__main__':
    unittest.main()
