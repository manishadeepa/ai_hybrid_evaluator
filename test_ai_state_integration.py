"""Offline state integration and real Excel assessment-scoping checks."""
import ast
import asyncio
import json
import os
from pathlib import Path
import tempfile
import time
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
method_names = {'run_ai_evaluation', 'run_all_candidates_ai_evaluation', '_start_ai_run', '_selected_ai_run', '_apply_ai_run', '_restore_selected_ai_run', 'execute_ai_run', 'set_selected_evaluation_candidate',
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
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if hasattr(self, 'progress_snapshots'):
            self.progress_snapshots.append((self.eval_progress_current, list(self.eval_progress_questions)))

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
    obj.active_ai_run_id = ""
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
        original_exists = Path.exists
        patch.object(Path, 'exists', lambda path: True if path.name in ('paper.xlsx', 'response.xlsx') else original_exists(path)).start()
        self.addCleanup(patch.stopall)
        self.progress_snapshots = []
        # The UI now dispatches a background event. Exercise that event with real run
        # persistence, while retaining the existing aggregate engine test doubles.
        from backend.services.ai_evaluation_run_service import AIEvaluationRunService
        from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        repository = AIEvaluationRunRepository(Path(directory.name)/'runs.json')
        owner = self
        class AdapterRunService(AIEvaluationRunService):
            def __init__(self):
                super().__init__(repository)
                self.invocations = {}

            def normalized(self, candidate, row):
                return {'candidate_id':candidate,'question_no':row['question_no'],
                        'question':row.get('question','Question'),'candidate_answer':'Answer',
                        'unanswered':row.get('unanswered',False),'max_marks':row.get('maximum_marks',10),
                        'answer_key':'Reference','question_type':'subjective',
                        'metadata':{k:row.get(k,question_result(candidate).get(k,'')) for k in ('co','lo','domain','knowledge_type','rbt_level')}}

            def prepare_single(self, assessment, test, candidate, label, paper, response, answer_key, **ids):
                fixture = owner.single.return_value
                rows = fixture.get('results', []) + fixture.get('errors', [])
                run = self.create_run(assessment,test,[self.normalized(candidate,r) for r in rows],labels={candidate:label},**ids)
                self.invocations[run['run_id']] = lambda: owner.single(str(paper),str(response),answer_key)
                return run

            def prepare_batch(self, assessment, test, rows, labels, paper, answer_key, skipped=None, **ids):
                normalized = [self.normalized(r['candidate_id'],dict(r,maximum_marks=float(r['maximum_marks']))) for r in rows]
                fixture = namespace['_evaluate_candidates_questionwise'].return_value
                if isinstance(fixture,dict):
                    existing={(r['candidate_id'],r['question_no']) for r in normalized}
                    for candidate, results in fixture.get('results_by_candidate',{}).items():
                        for row in results:
                            if (candidate,row['question_no']) not in existing:
                                normalized.append(self.normalized(candidate,row))
                run=self.create_run(assessment,test,normalized,candidate_scope='all',labels=labels,skipped=skipped,**ids)
                self.invocations[run['run_id']]=lambda: namespace['_evaluate_candidates_questionwise'](str(paper),rows,answer_key,progress_callback=lambda event:None)
                return run

            def execute(self, run_id):
                run=self.start(run_id);token=run['execution_token']
                try:
                    output=self.invocations[run_id]()
                    rows=([r for group in output['results_by_candidate'].values() for r in group]
                          if 'results_by_candidate' in output else output.get('results',[])+output.get('errors',[]))
                    while True:
                        chunk=self._next_chunk(run_id,token,1)
                        if not chunk: break
                        q=chunk[0];record=q['record']
                        row=next(r for r in rows if r['candidate_id']==record['candidate_id'] and r['question_no']==record['question_no'])
                        if row.get('status')=='failed' or row.get('error'):
                            self.checkpoint(run_id,token,q['pair_id'],error=row.get('error','Failed'))
                        else:
                            self.checkpoint(run_id,token,q['pair_id'],result=row)
                        time.sleep(0.12)  # allow background state polling to observe each checkpoint
                    return self.finish(run_id,token)
                except Exception as exc:
                    return self.finish(run_id,token,str(exc))
        service=AdapterRunService()
        def provider(): return service
        provider.result_rows=AIEvaluationRunService.result_rows
        namespace['AIEvaluationRunService']=provider
        namespace['FacilitatorState']=SimpleNamespace(execute_ai_run=lambda run_id:('execute',run_id), refresh_workspace_snapshot=lambda *args:('refresh',))

    async def consume(self, obj):
        obj.progress_snapshots = self.progress_snapshots
        async for value in obj.run_ai_evaluation():
            if isinstance(value, tuple) and value[0] == 'execute':
                async for message in obj.execute_ai_run(value[1]):
                    pass
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
        # Fresh AI-run display data is available immediately, while
        # report status represents finalized/persisted evaluation data.
        self.assertEqual(obj.results_eval_status, 'Not Evaluated')
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
        # In-memory AI results must not implicitly become finalized
        # assessment/reporting results.
        self.assertEqual(obj.assessment_evaluation_results, {})
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
