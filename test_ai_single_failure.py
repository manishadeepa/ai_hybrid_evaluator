"""Offline regression coverage; Azure responses are doubles, never production fallback."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pandas as pd
from ai_hybrid_evaluator.services import ai_evaluation_service as engine
import test_ai_state_integration as integration


class SingleServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paper = Path(self.temp.name) / 'paper.xlsx'
        self.response = Path(self.temp.name) / 'response.xlsx'
        rows = [{'Question No': f'Q{i}', 'Question': f'Question {i}', 'Marks': 2 if i <= 10 else 5,
                 'Answer Key': 'Reference', 'CO': 'CO1', 'LO': 'LO1', 'Knowledge Type': 'Conceptual',
                 'Domain': 'Cognitive', 'RBT level': 'Understand'} for i in range(1, 15)]
        pd.DataFrame(rows).to_excel(self.paper, index=False)
        pd.DataFrame([dict(r, **{'Candidate Answer': 'Actual answer' if i < 3 else ''})
                      for i, r in enumerate(rows)]).to_excel(self.response, index=False)
        self.client = Mock()
        self.calls = []
        def create(**kwargs):
            self.calls.append(kwargs['messages'][0]['content'])
            payload = {'awarded_marks': 2, 'percentage': 100,
                       'evaluation': {'correctness': 'Correct', 'relevance': 'Relevant', 'completeness': 'Complete',
                                      'strengths': [], 'missing_points': [], 'incorrect_points': []},
                       'justification': 'Correct answer'}
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
        self.client.chat.completions.create.side_effect = create
        self.loader = patch.object(engine, '_load_client', return_value=(self.client, 'test-deployment')).start()
        self.addCleanup(patch.stopall)

    def test_answered_calls_and_full_totals(self):
        result = engine.evaluate_candidate(self.paper, self.response)
        self.assertEqual(len(self.calls), 3)
        for i, prompt in enumerate(self.calls, 1):
            self.assertIn(f'Question {i}', prompt)
            self.assertIn('Actual answer', prompt)
        self.assertEqual([r['question_no'] for r in result['results']], [f'Q{i}' for i in range(1,15)])
        for row in result['results']:
            self.assertTrue(0 <= row['awarded_marks'] <= row['maximum_marks'])
        for row in result['results'][3:]:
            self.assertEqual(row['awarded_marks'], 0)
            self.assertEqual(row['justification'], 'Question not attempted by the candidate.')
        summary = result['candidate_summary_df'].iloc[0]
        self.assertEqual(summary['total_maximum_marks'], 40)
        self.assertEqual(summary['total_awarded_marks'], 6)
        self.assertEqual(summary['overall_percentage'], 15)
        self.assertEqual(result['errors'], [])

    def test_azure_failure_preserves_errors_and_suppresses_final_summary(self):
        self.client.chat.completions.create.side_effect = RuntimeError('404 DeploymentNotFound')
        with patch.object(engine.time, 'sleep'):
            result = engine.evaluate_candidate(self.paper, self.response)
        self.assertEqual(self.client.chat.completions.create.call_count, 9)
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(result['candidate_summary_df'].empty)
        self.assertEqual([e['question_no'] for e in result['errors']], ['Q1','Q2','Q3'])
        self.assertEqual(sum(e['maximum_marks'] for e in result['errors']), 6)
        self.assertTrue(all(e['awarded_marks'] is None for e in result['errors']))
        self.assertEqual(len(result['results']), 11)


class SingleStateTests(integration.IntegrationTests):
    async def test_single_partial_does_not_report_completed(self):
        obj = integration.state()
        obj.selected_evaluation_candidate = 'Alice (A)'
        obj.ai_evaluation_done = True
        self.single.return_value = {'results': [dict(integration.question_result('A'), unanswered=False)],
                                   'errors': [dict(integration.question_result('A', None, 'failed'), question_no='Q2')]}
        await self.consume(obj)
        saved = obj.real_ai_results_per_candidate['A:Assessment A:Test']
        self.assertEqual(saved['status'], 'partial')
        self.assertEqual(saved['score'], 'Incomplete')
        self.assertEqual(saved['max_marks'], 20)
        self.assertIsNone(saved['normalized_score'])
        self.assertEqual(len(saved['questions']), 2)
        self.assertFalse(obj.ai_evaluation_done)
        self.assertEqual(obj.assessment_evaluation_results, {})
        self.assertTrue(any(kind == 'error' and 'Q2' in text for kind, text in self.messages))
        self.assertFalse(any(kind == 'success' for kind, text in self.messages))

    async def test_single_fatal_error_cannot_leave_success_banner(self):
        obj = integration.state()
        obj.selected_evaluation_candidate = 'Alice (A)'
        obj.ai_evaluation_done = True
        self.single.side_effect = RuntimeError('404 DeploymentNotFound')
        await self.consume(obj)
        self.assertFalse(obj.ai_evaluation_done)
        self.assertFalse(obj.is_ai_evaluating)
        self.assertEqual(obj.real_ai_results_per_candidate, {})
        self.assertTrue(any(kind == 'error' and 'DeploymentNotFound' in text for kind, text in self.messages))

if __name__ == '__main__':
    unittest.main()
