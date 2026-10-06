"""Automatic paper ingestion and real response/checkpoint/result integration, offline."""
import ast
import csv
from io import BytesIO, StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import Workbook
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository
from backend.repositories.json_repository import JSONRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService
from backend.services.question_paper_service import QuestionPaperService, COLUMNS
from backend.services.response_lifecycle_service import ResponseLifecycleService
from backend.services.ai_evaluation_run_service import AIEvaluationRunService
from backend.services.evaluation_result_service import EvaluationResultService
from backend.services.question_type_schema import selected_option
from backend.services.manual_evaluation_service import ManualEvaluationService

ROOT = Path(__file__).parent
ENGINE = 'ai_hybrid_evaluator.services.ai_evaluation_service.'

def workbook(kind='objective', questions=None):
    book = Workbook(); book.active.append(COLUMNS)
    for i in range(1, 4):
        question = f'Question {i}'
        if kind == 'objective': question += '\nA) Alpha\nB) Beta\nC) Gamma\nD) Delta'
        if questions is not None: question = questions[i-1]
        book.active.append([f'Q{i}', question, i, 'CO1', 'LO1', 'Fact', 'Cognitive', 'Remember', 'B' if kind == 'objective' else 'Reference'])
    stream=BytesIO();book.save(stream);book.close();return stream.getvalue()

class AutomaticTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);previous=Path.cwd();os.chdir(self.root);self.addCleanup(os.chdir,previous)
        self.candidates=CandidateManagementService(CandidateRepository(self.root/'candidates.json'))
        self.assignments=CandidateAssignmentService(self.candidates)
        self.assessments=self.candidates.assessments;self.tests=self.assessments.tests
        self.a=self.assessments.create_assessment({'name':'Assessment','tests':['Test']})
        self.aid=self.a['assessment_id'];self.tid=self.a['test_ids']['Test']
        self.papers=QuestionPaperService(self.tests)
        self.responses=ResponseLifecycleService(self.assignments)
        self.runs=AIEvaluationRunService(AIEvaluationRunRepository(self.root/'runs.json'),self.tests)
        self.manual=object.__new__(ManualEvaluationRepository);self.manual.storage=JSONRepository(self.root/'manual.json')
        self.results=EvaluationResultService(candidates=self.candidates,manual_repository=self.manual,ai_repository=self.runs.repository)
        for cid in ('C1','C2'):
            self.candidates.create_candidate({'candidate_id':cid,'name':cid+' Name','email':cid+'@example.com'})
            self.assignments.assign_candidate_to_assessment(cid,self.aid)
            self.assignments.assign_candidate_to_test(cid,self.tid)

    def ingest(self,kind='objective'):
        self.paper=self.papers.import_upload(self.aid,self.tid,'paper.xlsx',workbook(kind))
        return self.paper

    def submit(self,cid='C1',answers=None):
        self.responses.start_test(cid,self.aid,self.tid)
        return self.responses.submit(cid,self.aid,self.tid,answers=answers if answers is not None else {'1':'B','2':'A','3':''})

    def prepare(self,cid='C1'):
        response=self.responses.get_response(cid,self.aid,self.tid)
        return self.runs.prepare_single('Assessment','Test',cid,cid,self.papers.upload_dir/self.paper['filename'],response['response_file'],
            assessment_id=self.aid,test_id=self.tid)

    def execute_local(self,run):
        # Objective questions now use the AI evaluation lifecycle.
        # Tests mock the AI result while preserving objective 0/full grading.
        def objective_result(row):
            import backend.services.question_type_schema as question_schema

            # Reconstruct the canonical Objective question structure
            # expected by evaluate_objective().
            question_text = str(row.get("question") or "")
            options = {}

            for line in question_text.splitlines():
                line = line.strip()

                if (
                    len(line) >= 3
                    and line[0].upper() in "ABCD"
                    and line[1] == ")"
                ):
                    options[line[0].upper()] = line[2:].strip()

            correct_option = str(
                row.get("answer_key") or ""
            ).strip().upper()

            question = {
                "correct_option": correct_option,
                "options": options,
            }

            result = question_schema.evaluate_objective(row, question)

            max_marks = row["max_marks"]
            awarded = result["awarded_marks"]

            result.update(
                {
                    "maximum_marks": max_marks,
                    "percentage": (
                        0
                        if not max_marks
                        else round(
                            (awarded / max_marks) * 100,
                            2,
                        )
                    ),
                    "evaluation": {
                        "correctness": result["answer_status"],
                        "relevance": "",
                        "completeness": "",
                        "strengths": [],
                        "missing_points": [],
                        "incorrect_points": [],
                    },
                    "status": (
                        "unanswered"
                        if row.get("unanswered")
                        else "completed"
                    ),
                    "attempts": (
                        0 if row.get("unanswered") else 1
                    ),
                }
            )

            return result

        def fake_single(
            client,
            deployment,
            row,
            max_retries=3,
            delay_seconds=2,
        ):
            return objective_result(row)

        def fake_batch(
            client,
            deployment,
            rows,
            max_retries=3,
            delay_seconds=2,
            result_callback=None,
        ):
            results = []

            for row in rows:
                result = objective_result(row)
                result["response_id"] = row["response_id"]
                results.append(result)

                if result_callback:
                    result_callback(row["response_id"], result)

            return results

        with patch(
            ENGINE + "_load_client",
            return_value=(object(), "test-deployment"),
        ), patch(
            ENGINE + "_evaluate_with_retry",
            side_effect=fake_single,
        ), patch(
            ENGINE + "_evaluate_question_batch",
            side_effect=fake_batch,
        ):
            result = self.runs.execute(run["run_id"])

        return result

    def test_detection_and_atomic_replacement(self):
        self.ingest('subjective');self.assertEqual(self.tests.get_test(self.tid)['test_type'],'subjective')
        self.ingest();self.assertEqual(self.tests.get_test(self.tid)['test_type'],'objective')
        before=self.tests.repository.file_path.read_bytes()
        for questions in (['Plain','Stem\nA) Alpha','Plain'], ['Plain','Stem\nA) A\nB) B\nC) C\nD) D','Plain']):
            with self.assertRaises(ValueError):self.papers.import_upload(self.aid,self.tid,'bad.xlsx',workbook(questions=questions))
            self.assertEqual(before,self.tests.repository.file_path.read_bytes())

    def test_invalid_keys_and_malformed_options(self):
        for key in ('','E','A,B','A) Wrong'):
            from test_test_type_support import workbook as one
            with self.subTest(key=key),self.assertRaises(ValueError):self.papers.validate_workbook(one(answer=key),'paper.xlsx')
        from test_test_type_support import workbook as one
        for question in ('Stem A) Alpha B) Beta C) Gamma D) Delta', 'Stem\nA)\nB) B\nC) C\nD) D','Stem\na) A\nb) B\nc) C\nd) D'):
            with self.assertRaises(ValueError):self.papers.validate_workbook(one(question),'paper.xlsx')

    def test_single_response_results_and_csv(self):
        self.ingest();response=self.submit()
        self.assertEqual(response['test_type'],'objective')
        self.assertTrue(Path(response['response_file']).is_file())
        self.assertTrue(all(q['options']['B'] == 'Beta' for q in response['questions']))
        self.assertTrue(all('correct_option' not in q for q in response['questions']))
        run=self.execute_local(self.prepare());self.assertEqual(run['status'],'completed',run['error'])
        value=self.results.get_result('C1',self.aid,self.tid)
        self.assertEqual((value['total_marks'],value['max_marks'],value['percentage']),(1,6,16.67))
        by_no = {q['question_no']: q for q in value['questions']}
        self.assertEqual(by_no['Q1']['awarded_marks'], 1)
        self.assertEqual(by_no['Q2']['awarded_marks'], 0)
        self.assertEqual(by_no['Q3']['awarded_marks'], 0)
        self.assertEqual(by_no['Q1']['answer_status'], 'Correct')
        self.assertEqual(by_no['Q2']['answer_status'], 'Incorrect')
        self.assertEqual(by_no['Q3']['answer_status'], 'Unanswered')
        rows=list(csv.DictReader(StringIO(self.results.export_csv(assessment_id=self.aid,test_id=self.tid).decode('utf-8-sig'))))
        self.assertEqual(len(rows), 3)
        rows_by_no = {r['question_no']: r for r in rows}
        self.assertEqual(rows_by_no['Q1']['candidate_answer'], 'B')
        self.assertEqual(rows_by_no['Q1']['correct_option'], 'B')
        rows_by_no = {r['question_no']: r for r in rows}
        self.assertEqual(rows_by_no['Q3']['answer_status'],'Unanswered')
        self.assertTrue(all(r['test_id'] == self.tid for r in rows))

    def test_all_candidates_and_labelled_answers(self):
        self.ingest();self.submit();self.submit('C2',{'1':'b','2':'B) Beta','3':'B) Wrong'})
        rows=[]
        for cid in ('C1','C2'):rows.extend(q['record'] for q in self.prepare(cid)['questions'])
        # Remove only temporary prepared runs before making the cohort run.
        self.runs.repository.file_path.unlink()
        run=self.runs.prepare_batch('Assessment','Test',rows,{},self.papers.upload_dir/self.paper['filename'],assessment_id=self.aid,test_id=self.tid)
        run=self.execute_local(run);self.assertEqual(run['status'],'completed',run['error'])
        results=self.results.list_results();self.assertEqual(len(results),2)
        self.assertEqual({r['candidate_id']:r['total_marks'] for r in results},{'C1':1,'C2':3})
        self.assertEqual(run['completed_questions'],6)

    def test_legacy_and_cross_assessment_fail_before_azure(self):
        from test_ai_evaluation_runs import records
        run=self.runs.create_run('Assessment','Test',records(),assessment_id=self.aid,test_id=self.tid)
        failed=self.execute_local(run);self.assertEqual(failed['status'],'failed');self.assertIn('upload',failed['error'])
        self.ingest();self.submit();run=self.prepare();run['assessment_id']='wrong';self.runs.repository.save(run)
        failed=self.execute_local(run);self.assertEqual(failed['status'],'failed');self.assertIn('assessment',failed['error'])

    def test_wrong_candidate_unsubmitted_and_tampered_input_rejected(self):
        self.ingest();self.submit();run=self.prepare()
        for q in run['questions']:q['record']['candidate_id']='C2'
        run['candidate_ids']=['C2'];run['candidate_id']='C2';self.runs.repository.save(run)
        failed=self.execute_local(run);self.assertIn('finalized submission',failed['error'])
        run=self.prepare()
        target = next(q for q in run['questions'] if q['record']['question_no'] == 'Q1')
        target['record']['candidate_answer'] = 'A'
        self.runs.repository.save(run)
        self.assertIn('differs',self.execute_local(run)['error'])

    def test_missing_question_not_success(self):
        self.ingest();self.submit();run=self.prepare();run['questions'].pop();self.runs.repository.save(run)
        failed=self.execute_local(run);self.assertEqual(failed['status'],'failed');self.assertIn('every question',failed['error'])

    def test_subjective_single_and_batch_use_existing_engine(self):
        self.ingest('subjective');self.submit()
        run=self.prepare()
        with patch(ENGINE+'_load_client',return_value=(object(),'deployment')) as client, patch(ENGINE+'_evaluate_with_retry',return_value={'awarded_marks':0,'justification':'Existing engine'}) as grade:
            self.assertEqual(self.runs.execute(run['run_id'])['status'],'completed');client.assert_called_once();self.assertEqual(grade.call_count,3)
        rows=[q['record'] for q in run['questions']]
        run=self.runs.prepare_batch('Assessment','Test',rows,{},self.papers.upload_dir/self.paper['filename'],assessment_id=self.aid,test_id=self.tid)
        with patch(ENGINE+'_load_client',return_value=(object(),'deployment')) as client, patch(ENGINE+'_evaluate_question_batch',side_effect=lambda c,d,rows,*args:[{'awarded_marks':0,'justification':'Batch'} for r in rows]) as grade:
            self.assertEqual(self.runs.execute(run['run_id'])['status'],'completed');client.assert_called_once();self.assertEqual(grade.call_count,3)
        self.assertIn('Batch',self.results.export_csv().decode('utf-8-sig'))

    def test_manual_precedence_and_report(self):
        self.ingest();self.submit();self.execute_local(self.prepare())
        ManualEvaluationService(self.manual).evaluate_and_save('C1','Assessment','Test',[dict(q_no='Q1',question='Review',response='B',max_marks=1,awarded_marks=0,justification='Manual review')])
        value=self.results.get_result('C1',self.aid,self.tid);self.assertEqual(value['evaluation_type'],'manual')
        self.assertIn('Manual review',self.results.export_csv().decode('utf-8-sig'))

    def test_label_normalization_no_semantic_comparison(self):
        choices=dict(zip('ABCD',('Alpha','Beta','Gamma','Delta')))
        for text in ('Beta','A,B','B) Wrong','Probably B'):
            self.assertIsNone(selected_option(text,choices))
        self.assertEqual(selected_option(' b ',choices),'B')

    def test_objective_stop_resume_and_restart(self):
        from backend.services.question_type_schema import evaluate_objective
        self.ingest();self.submit();run=self.prepare();calls=[]
        def grade(record, question):
            calls.append(record['question_no'])
            if len(calls)==1:self.runs.request_stop(run['run_id'])
            return evaluate_objective(record,question)
        with patch('backend.services.question_type_schema.evaluate_objective',side_effect=grade):
            paused=self.execute_local(run);self.assertEqual(paused['status'],'paused')
            finished=self.execute_local(paused);self.assertEqual(finished['status'],'completed')
        self.assertEqual(set(calls), {'Q1','Q2','Q3'})
        self.assertEqual(len(calls), 3)
        restarted=self.runs.restart(run['run_id'])
        self.assertEqual(self.execute_local(restarted)['completed_questions'],3)

    def test_candidate_state_uses_safe_canonical_snapshot(self):
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock
        self.ingest();self.responses.start_test('C1',self.aid,self.tid)
        self.responses.save_answer('C1',self.aid,self.tid,1,'B')
        source=ast.parse((ROOT/'ai_hybrid_evaluator/state/candidate_state.py').read_text(encoding='utf-8'))
        cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='CandidateState')
        method=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start_test')
        state=SimpleNamespace(_get_current_candidate_id=AsyncMock(return_value='C1'),max_violations=3,timer_session_id=0,_save_current_test_record=Mock())
        rx=SimpleNamespace(call_script=lambda script:script,redirect=lambda url:url,toast=SimpleNamespace(error=lambda text: (_ for _ in ()).throw(AssertionError(text))))
        loaded={}
        namespace={'asyncio':asyncio,'AssessmentService':lambda:self.assessments,'ResponseLifecycleService':lambda:self.responses,
                   'PERSISTED_CANDIDATE_TEST_DATA':{},'LOADED_TEST_QUESTIONS':loaded,'rx':rx,'CandidateState':SimpleNamespace(run_timer='timer')}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'candidate','exec'),namespace)
        asyncio.run(namespace['start_test'](state,'Assessment','Test'))
        self.assertEqual(state.mcq_answers,{'1':'B'});self.assertEqual(state.answers,{})
        question=next(q for q in state.questions if q['id'] == 1)
        self.assertEqual(question['text'],'Question 1');self.assertEqual(question['options']['B'],'Beta')
        self.assertNotIn('correct_option',question)
        self.assertIn('A)',self.responses.get_response('C1',self.aid,self.tid)['questions'][0]['text'])

    def test_wrong_workbook_identity_and_missing_type_preparation(self):
        self.ingest();self.submit();other=self.submit('C2')
        with self.assertRaisesRegex(ValueError,'does not belong'):
            self.runs.prepare_single('Assessment','Test','C1','C1',self.papers.upload_dir/self.paper['filename'],other['response_file'],assessment_id=self.aid,test_id=self.tid)
        legacy=self.tests.create_test(self.aid,{'test_name':'Legacy'})
        with self.assertRaisesRegex(ValueError,'upload'):
            self.runs.prepare_single('Assessment','Legacy','C1','C1','unused','unused',assessment_id=self.aid,test_id=legacy['test_id'])
        self.assertEqual(self.runs.repository.get_all(),[])

    def test_existing_download_handler_returns_download_event(self):
        source=ast.parse((ROOT/'ai_hybrid_evaluator/state/facilitator_state.py').read_text(encoding='utf-8'))
        cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='FacilitatorState')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_download_evaluation_csv')
        self.ingest();self.submit();self.execute_local(self.prepare())
        from types import SimpleNamespace
        rx=SimpleNamespace(download=lambda **kw:kw,toast=SimpleNamespace(error=lambda text: (_ for _ in ()).throw(AssertionError(text))))
        namespace={'rx':rx};exec(compile(ast.Module(body=[method],type_ignores=[]),'download','exec'),namespace)
        with patch(
            'backend.services.evaluation_result_service.EvaluationResultService',
            return_value=self.results,
        ), patch(
            'backend.services.test_service.TestService',
            return_value=self.tests,
        ):
            event=namespace['_download_evaluation_csv'](
                SimpleNamespace(selected_assessment_name='Assessment'),
                'Test',
                'C1',
            )
        self.assertTrue(event['filename'].endswith('_Question_Wise_Results.xlsx'))
        self.assertTrue(event['data'])

if __name__=='__main__':unittest.main()
