"""Offline state integration and real Excel assessment-scoping checks."""
import ast
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_hybrid_evaluator.services import ai_evaluation_service as engine
from ai_hybrid_evaluator.services import candidate_response_service as responses

STATE_PATH = Path('ai_hybrid_evaluator/state/facilitator_state.py')
tree = ast.parse(STATE_PATH.read_text(encoding='utf-8'))
state_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FacilitatorState')
helper_names = {'_evaluation_candidate_id', '_assessment_result_view', '_saved_evaluation', '_batch_candidate_display'}
method_names = {'run_ai_evaluation', 'run_all_candidates_ai_evaluation', 'set_selected_evaluation_candidate',
                'set_evaluation_selected_test', 'evaluation_candidate_options', 'assessment_evaluation_results',
                'open_manual_eval_modal', 'save_manual_evaluation', 'results_eval_status'}
namespace = {'asyncio': asyncio, 'Path': Path, 'datetime': datetime}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in helper_names:
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(STATE_PATH), 'exec'), namespace)
for node in state_class.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in method_names:
        node.decorator_list = []
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(STATE_PATH), 'exec'), namespace)


class StateHarness:
    @property
    def my_assessments(self):
        async def value():
            return self.assessments
        return value()

for name in method_names:
    method = namespace[name]
    setattr(StateHarness, name, property(method) if name in ('assessment_evaluation_results', 'results_eval_status') else method)


def state():
    obj = StateHarness()
    obj.selected_assessment_name = 'Assessment A'
    obj.selected_test_name = 'Test'
    obj.selected_evaluation_candidate = 'All Candidates'
    obj.results_selected_candidate = 'Alice (A)'
    obj.results_selected_test = 'Test'
    obj.is_ai_evaluating = False
    obj.answer_key_uploaded = False
    obj.answer_key_uploaded_path = ''
    obj.question_papers = {'Assessment A': {'Test': 'paper.xlsx'}}
    obj.real_ai_results_per_candidate = {}
    obj.ai_candidates_data = {}
    obj.assessments = [
        {'name': 'Assessment A', 'candidate_details': [{'emp_id': 'A', 'name': 'Alice'}, {'emp_id': 'B', 'name': 'Bob'}, {'emp_id': 'M', 'name': 'Missing'}]},
        {'name': 'Assessment B', 'candidate_details': [{'emp_id': 'X', 'name': 'Other'}]},
    ]
    obj._get_question_count_from_qp = lambda path: 1
    return obj


def question_result(candidate_id, marks=4, status='completed'):
    row = {'candidate_id': candidate_id, 'question_no': 'Q1', 'question': 'Question',
           'candidate_answer': 'Answer', 'maximum_marks': 10, 'awarded_marks': marks,
           'percentage': marks * 10 if marks is not None else None, 'status': status,
           'co': 'CO1', 'lo': 'LO1', 'rbt_level': 'Understand', 'domain': 'Cognitive',
           'knowledge_type': 'Conceptual', 'justification': 'Feedback'}
    if status == 'failed':
        row['error'] = 'Invalid AI output'
    return row


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.messages = []
        toast = SimpleNamespace(**{kind: (lambda message, k=kind: (self.messages.append((k, message)), (k, message))[1])
                                   for kind in ('info', 'warning', 'success', 'error')})
        namespace['rx'] = SimpleNamespace(toast=toast, get_upload_dir=lambda: Path('uploads'))
        self.single = Mock(return_value={'results': [dict(question_result('A'), unanswered=False)], 'candidate_summary_df': None})
        self.lookups = []
        def lookup(**kwargs):
            self.lookups.append(kwargs)
            if kwargs['candidate_id'] == 'M':
                return {}
            return {'responses': [{'q_no': 'Q1', 'question': 'Question', 'response': 'Answer', 'max_marks': '10', 'CO': 'CO1'}]}
        self.lookup = Mock(side_effect=lookup)
        namespace['_evaluate_candidate'] = self.single
        namespace['get_latest_candidate_response'] = self.lookup
        namespace['_find_response_file_path'] = Mock(return_value=Path('response.xlsx'))
        patch.object(Path, 'exists', return_value=True).start()
        self.addCleanup(patch.stopall)
        self.progress_snapshots = []

    async def consume(self, obj):
        async for value in obj.run_ai_evaluation():
            self.progress_snapshots.append((getattr(obj, 'eval_progress_current', 0), list(getattr(obj, 'eval_progress_questions', []))))

    async def test_all_routing_keys_independence_and_skips(self):
        def batch(path, records, key, progress_callback):
            self.assertEqual([r['candidate_id'] for r in records], ['A', 'B'])
            self.assertEqual(records[0]['assessment_name'], 'Assessment A')
            self.assertEqual(records[0]['maximum_marks'], '10')
            progress_callback({'question_index': 1, 'total': 1, 'status': 'evaluating'})
            progress_callback({'question_index': 1, 'total': 1, 'status': 'completed'})
            return {'results_by_candidate': {'A': [question_result('A', 4)], 'B': [question_result('B', 8)]}, 'errors': []}
        namespace['_evaluate_candidates_questionwise'] = Mock(side_effect=batch)
        obj = state()
        await self.consume(obj)
        self.single.assert_not_called()
        namespace['_evaluate_candidates_questionwise'].assert_called_once()
        self.assertEqual(set(obj.real_ai_results_per_candidate), {'A:Assessment A:Test', 'B:Assessment A:Test'})
        self.assertEqual(obj.real_ai_results_per_candidate['A:Assessment A:Test']['score'], '4 / 10')
        self.assertEqual(obj.real_ai_results_per_candidate['B:Assessment A:Test']['co'][0]['score'], 80)
        self.assertTrue(all(c['require_assessment_scope'] for c in self.lookups))
        self.assertEqual(obj.batch_evaluation_errors[0]['candidate_id'], 'M')
        self.assertEqual(obj.batch_evaluation_errors[0]['status'], 'skipped')
        self.assertTrue(any(index == 1 for index, rows in self.progress_snapshots))
        self.assertFalse(obj.is_ai_evaluating)
        self.assertFalse(obj.show_eval_progress_modal)
        obj.set_selected_evaluation_candidate('Alice (A)')
        self.assertEqual(obj.real_ai_score_display, '4 / 10')
        self.assertEqual(obj.results_eval_status, 'Evaluated')
        obj.selected_assessment_name = 'Assessment B'
        obj.set_selected_evaluation_candidate('Alice (A)')
        self.assertEqual(obj.real_ai_score_display, '—')
        self.assertEqual(obj.assessment_evaluation_results, {})

    async def test_single_routing_and_display(self):
        namespace['_evaluate_candidates_questionwise'] = Mock()
        obj = state()
        obj.selected_evaluation_candidate = 'Alice (A)'
        await self.consume(obj)
        self.single.assert_called_once()
        namespace['_evaluate_candidates_questionwise'].assert_not_called()
        self.assertIn('A:Assessment A:Test', obj.real_ai_results_per_candidate)
        obj.set_selected_evaluation_candidate('Alice (A)')
        self.assertEqual(obj.real_ai_score_display, '4 / 10')

    async def test_partial_kept_without_zero_score_or_completed_report(self):
        failed = question_result('B', None, 'failed')
        good_b = dict(question_result('B', 3), question_no='Q2')
        namespace['_evaluate_candidates_questionwise'] = Mock(return_value={
            'results_by_candidate': {'A': [question_result('A')], 'B': [failed, good_b]}, 'errors': [failed]})
        obj = state()
        await self.consume(obj)
        partial = obj.real_ai_results_per_candidate['B:Assessment A:Test']
        self.assertIsNone(partial['normalized_score'])
        self.assertIsNone(partial['questions'][0]['awarded_marks'])
        self.assertEqual(partial['questions'][1]['awarded_marks'], 3)
        self.assertNotIn('Bob (B):Test', obj.assessment_evaluation_results)
        obj.set_selected_evaluation_candidate('Bob (B)')
        self.assertEqual(obj.real_ai_score_display, 'Incomplete')
        self.assertTrue(any(kind == 'warning' for kind, text in self.messages))

    async def test_no_submissions_and_manual_guard(self):
        namespace['_evaluate_candidates_questionwise'] = Mock()
        namespace['get_latest_candidate_response'] = Mock(return_value={})
        obj = state()
        await self.consume(obj)
        namespace['_evaluate_candidates_questionwise'].assert_not_called()
        self.assertEqual(obj.real_ai_results_per_candidate, {})
        self.assertEqual(len(obj.batch_evaluation_errors), 3)
        obj.open_manual_eval_modal()
        obj.save_manual_evaluation()
        self.assertIn('manual evaluation', self.messages[-1][1])

    async def test_selector_and_legacy_fallback(self):
        obj = state()
        options = await obj.evaluation_candidate_options()
        self.assertEqual(options, ['All Candidates', 'Alice (A)', 'Bob (B)', 'Missing (M)'])
        legacy = {'score': '2 / 10', 'percentage': '20%', 'max_score': '10', 'questions': []}
        obj.real_ai_results_per_candidate['Alice (A):Test'] = legacy
        obj.set_selected_evaluation_candidate('Alice (A)')
        self.assertEqual(obj.real_ai_score_display, '2 / 10')
        obj.real_ai_results_per_candidate['A:Assessment A:Test'] = namespace['_batch_candidate_display']('A', 'Alice (A)', 'Assessment A', 'Test', [question_result('A')])
        self.assertEqual(len(obj.assessment_evaluation_results), 1)
        self.assertIn('Alice (A):Test', obj.real_ai_results_per_candidate)


class ResponseScopeTests(unittest.TestCase):
    def test_real_workbook_scope_and_legacy_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            old = os.getcwd()
            try:
                os.chdir(directory)
                question = {'id': '1', 'title': 'Q1', 'text': 'Question', 'marks': 10,
                            'co': 'CO1', 'lo': 'LO1', 'knowledge_type': 'Conceptual', 'category': 'Cognitive', 'rbt_level': 'Understand'}
                first = responses.save_candidate_response('A', 'Alice', 'Assessment A', 'Test', [question], {'1': ''})
                second = responses.save_candidate_response('A', 'Alice', 'Assessment B', 'Test', [question], {'1': 'Other answer'})
                found = responses.find_candidate_response_file('A', 'Alice', 'Assessment A', 'Test', require_assessment_scope=True)
                self.assertEqual(str(found), first)
                self.assertNotEqual(first, second)
                loaded = responses.get_latest_candidate_response('A', 'Alice', 'Assessment A', 'Test', require_assessment_scope=True)
                self.assertEqual(loaded['responses'][0]['response'], '')
                self.assertIsNone(responses.find_candidate_response_file('A', 'Alice', 'Unknown', 'Test', require_assessment_scope=True))
                import pandas as pd
                legacy = Path('uploaded_files/candidate_responses/Legacy_Test_Response.xlsx')
                pd.DataFrame({'Question No': ['Q1'], 'Question': ['Question'], 'Candidate Answer': ['Legacy'], 'Marks': [10]}).to_excel(legacy, index=False)
                self.assertIsNone(responses.find_candidate_response_file('Legacy', 'Legacy', 'Assessment A', 'Test', require_assessment_scope=True))
                self.assertEqual(responses.find_candidate_response_file('Legacy', 'Legacy', 'Assessment A', 'Test'), legacy)
            finally:
                os.chdir(old)


class ProgressCallbackTests(unittest.TestCase):
    def test_existing_response_title_resolves_to_paper_number(self):
        from test_ai_questionwise import paper
        rows = [{"candidate_id": "A", "question_no": "Descriptive title", "question": "Question 1", "candidate_answer": ""}]
        with patch.object(engine, "_load_question_data", return_value=paper()), patch.object(engine, "_load_client") as client:
            result = engine.evaluate_candidates_questionwise("unused", rows)
        self.assertEqual(result["results"][0]["question_no"], "Q1")
        client.assert_not_called()

    def test_callback_follows_actual_question_batches(self):
        from test_ai_questionwise import paper, records
        timeline = []
        def evaluate(client, deployment, rows, *args):
            timeline.append(("batch", rows[0]["question_no"]))
            return [dict(question_result(r["candidate_id"]), response_id=r["response_id"]) for r in rows]
        with patch.object(engine, "_load_question_data", return_value=paper()), patch.object(engine, "_load_client", return_value=(None, None)), patch.object(engine, "_evaluate_question_batch", side_effect=evaluate):
            engine.evaluate_candidates_questionwise("unused", records(), batch_size=2,
                progress_callback=lambda event: timeline.append((event["status"], event["question_no"])))
        self.assertEqual(timeline, [(status, q) for q in ("Q1", "Q2")
                                    for status in ("evaluating", "batch", "batch", "completed")])


if __name__ == '__main__':
    unittest.main()
