"""Offline tests: no Azure calls, environment loading, or persistence writes."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_hybrid_evaluator.services import ai_evaluation_service as service


def grade(response_id, marks=4):
    return {"response_id": response_id, "awarded_marks": marks, "percentage": 999,
            "evaluation": {"correctness": "correct", "relevance": "relevant",
                           "completeness": "partial", "strengths": ["clear"],
                           "missing_points": ["detail"], "incorrect_points": []},
            "justification": "Partial credit"}


def paper():
    return {f"Question {n}": {"question_no": f"Q{n}", "max_marks": 10,
            "answer_key": f"Reference {n}", "co": "CO1", "lo": "LO1",
            "knowledge_type": "Conceptual", "domain": "Cognitive", "rbt_level": "Understand"}
            for n in (1, 2)}


def records():
    # Deliberately candidate-major: the orchestrator must reorder this.
    return [{"candidate_id": name, "question_no": f"Q{n}", "candidate_answer": "Answer"}
            for name in ("Alice", "Bob", "Carol") for n in (1, 2)]


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.prompts = []
        self.client = Mock()
        self.behavior = lambda answers: {"results": [grade(a["response_id"]) for a in answers]}
        def create(**kwargs):
            prompt = kwargs["messages"][0]["content"]
            self.prompts.append(prompt)
            answers = json.loads(prompt.split("STUDENT ANSWER:\n", 1)[1].split("\n\nMAXIMUM MARKS:", 1)[0])
            payload = self.behavior(answers)
            content = payload if isinstance(payload, str) else json.dumps(payload)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        self.client.chat.completions.create.side_effect = create
        self.loader = patch.object(service, "_load_question_data", return_value=paper()).start()
        self.client_loader = patch.object(service, "_load_client", return_value=(self.client, "mock")).start()
        self.addCleanup(patch.stopall)

    def run_batch(self, rows=None, **kwargs):
        return service.evaluate_candidates_questionwise("unused.xlsx", records() if rows is None else rows,
                                                       delay_seconds=0, **kwargs)

    def test_order_context_identity_and_percentage(self):
        result = self.run_batch(batch_size=3)
        self.assertEqual(len(self.prompts), 2)
        self.assertEqual([(r['question_no'], r['candidate_id']) for r in result['results']],
                         [(f'Q{n}', c) for n in (1, 2) for c in ('Alice', 'Bob', 'Carol')])
        for r in result['results']:
            self.assertEqual(r['percentage'], 40)
            self.assertEqual(r['co'], 'CO1')
            self.assertEqual(len(r['response_id']), 32)
        for prompt in self.prompts:
            self.assertNotIn('Alice', prompt)
            self.assertNotIn('Bob', prompt)
            self.assertNotIn('Carol', prompt)
            self.assertEqual(prompt.count('REFERENCE ANSWER (answer key):'), 1)
        self.assertEqual(len(result['results_by_candidate']['Alice']), 2)
        self.loader.assert_called_once()
        json.dumps(result, allow_nan=False)

    def test_invalid_marks(self):
        for invalid in (-1, 11, '4', True, float('nan'), float('inf')):
            with self.subTest(marks=invalid):
                self.behavior = lambda answers: {'results': [grade(a['response_id'], invalid) for a in answers]}
                result = self.run_batch(records()[:1], max_retries=1)
                self.assertEqual(result['results'][0]['status'], 'failed')
                self.assertIsNone(result['results'][0]['awarded_marks'])

    def test_duplicate_id(self):
        self.behavior = lambda a: {'results': [grade(a[0]['response_id']), grade(a[0]['response_id'])]}
        self.assertEqual(self.run_batch(records()[:1], max_retries=1)['results'][0]['status'], 'failed')

    def test_unexpected_id(self):
        self.behavior = lambda a: {'results': [grade(a[0]['response_id']), grade('unexpected')]}
        self.assertTrue(self.run_batch(records()[:1], max_retries=1)['errors'])

    def test_malformed(self):
        for payload in ('not JSON', {'results': [{}]}, {'results': [{'response_id': 'wrong'}]}):
            self.behavior = lambda a: payload
            self.assertTrue(self.run_batch(records()[:1], max_retries=1)['errors'])
        self.behavior = lambda a: {'results': [{'response_id': a[0]['response_id'], 'awarded_marks': 4}]}
        self.assertTrue(self.run_batch(records()[:1], max_retries=1)['errors'])

    def test_blank_answers_no_client(self):
        rows = [dict(records()[0], candidate_answer=value, candidate_id=str(i))
                for i, value in enumerate(('', '  ', None, float('nan')))]
        result = self.run_batch(rows)
        self.client_loader.assert_not_called()
        self.assertTrue(all(r['status'] == 'unanswered' and r['awarded_marks'] == 0 for r in result['results']))

    def test_partial_retry_before_next_question(self):
        requests = []
        def behavior(answers):
            requests.append([a['response_id'] for a in answers])
            # Omit one result on first attempt, retain the other two.
            return {'results': [grade(a['response_id']) for a in (answers[:2] if len(requests) == 1 else answers)]}
        self.behavior = behavior
        result = self.run_batch(batch_size=3)
        self.assertEqual([len(r) for r in requests], [3, 1, 3])
        self.assertEqual(requests[1], [requests[0][2]])
        self.assertIn('QUESTION:\nQuestion 1', self.prompts[1])
        self.assertIn('QUESTION:\nQuestion 2', self.prompts[2])
        self.assertFalse(result['errors'])

    def test_chunk_bound_and_duplicate_input(self):
        self.run_batch(batch_size=2)
        self.assertEqual(len(self.prompts), 4)
        with self.assertRaises(ValueError):
            self.run_batch([records()[0], records()[0]])

    def test_separate_key_loaded_once(self):
        import pandas as pd
        with patch.object(service.pd, 'read_excel', return_value=pd.DataFrame({'Question': ['Question 1'], 'Answer': ['Override']})) as read:
            self.run_batch(answer_key_path='key.xlsx')
        read.assert_called_once()
        self.assertIn('REFERENCE ANSWER (answer key):\nOverride', self.prompts[0])

    def test_single_candidate_existing_path(self):
        self.client.chat.completions.create.side_effect = lambda **kw: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(grade('ignored'))))])
        with patch.object(service.Path, 'exists', return_value=True), patch.object(service, '_load_candidate_data', return_value=[{
            'candidate_id': 'A', 'candidate_name': 'A', 'question_no': 'Q1',
            'question': 'Question 1', 'candidate_answer': 'Answer', 'unanswered': False}]):
            result = service.evaluate_candidate('paper.xlsx', 'responses.xlsx')
        self.assertEqual(result['candidate_summary_df'].iloc[0]['total_awarded_marks'], 4)
        self.assertIn('co_analysis_df', result)


if __name__ == '__main__':
    unittest.main()
