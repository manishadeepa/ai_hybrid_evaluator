"""Offline lifecycle regressions, isolated run persistence."""
import tempfile
import unittest
import threading
from unittest.mock import patch
from pathlib import Path
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.services.ai_evaluation_run_service import AIEvaluationRunService


def records(candidate='C1', count=3):
    return [{'candidate_id':candidate,'question_no':f'Q{i}','question':f'Question {i}',
             'candidate_answer':'Answer','unanswered':False,'answer_key':'Reference','max_marks':2,
             'metadata':{'co':'CO1','lo':'LO1','knowledge_type':'Conceptual','domain':'Cognitive','rbt_level':'Understand'}}
            for i in range(1,count+1)]


def result():
    return {'awarded_marks':1,'justification':'Partial credit','percentage':50}


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=AIEvaluationRunRepository(Path(self.temp.name)/'runs.json')
        self.service=AIEvaluationRunService(self.repo)
        from backend.services.assessment_service import AssessmentService
        from backend.repositories.assessment_repository import AssessmentRepository
        assessments=AssessmentService(AssessmentRepository(Path(self.temp.name)/'assessments.json'), self.service.tests)
        assessment=assessments.create_assessment({'name':'Assessment'})
        test=self.service.tests.create_test(assessment['assessment_id'], {'test_name':'Test','test_type':'subjective'})
        self.ids={'assessment_id':assessment['assessment_id'],'test_id':test['test_id']}

    def create(self, **kwargs):
        return self.service.create_run('Assessment','Test',records(),**self.ids,**kwargs)

    def test_creation_progress_and_reload(self):
        run=self.create();self.assertEqual(run['status'],'idle')
        self.assertEqual(run['completed_questions'],0);self.assertEqual(run['pending_questions'],3)
        self.assertEqual(run['candidate_id'],'C1')
        self.assertEqual(AIEvaluationRunService(self.repo).get_run(run['run_id']),run)

    def test_checkpoint_stop_resume_and_progress(self):
        run=self.service.start(self.create()['run_id']);rid=run['run_id'];token=run['execution_token']
        q=self.service._next_chunk(rid,token,1)[0]
        self.service.request_stop(rid)
        run=self.service.checkpoint(rid,token,q['pair_id'],result())
        self.assertEqual(run['completed_questions'],1);self.assertAlmostEqual(run['percentage'],100/3)
        self.assertEqual(self.service._next_chunk(rid,token,1),[])
        self.assertEqual(self.service.finish(rid,token)['status'],'paused')
        run=self.service.start(rid)
        self.assertEqual(self.service._next_chunk(rid,run['execution_token'],1)[0]['record']['question_no'],'Q2')

    def test_restart_isolation_and_late_old_result(self):
        old=self.service.start(self.create()['run_id']);token=old['execution_token']
        q=self.service._next_chunk(old['run_id'],token,1)[0]
        new=self.service.restart(old['run_id'])
        self.assertNotEqual(new['run_id'],old['run_id'])
        self.assertEqual(new['restarted_from_run_id'],old['run_id'])
        self.service.checkpoint(old['run_id'],token,q['pair_id'],result())
        self.assertEqual(self.service.get_run(new['run_id'])['completed_questions'],0)
        self.assertEqual(self.service._next_chunk(old['run_id'],token,1),[])
        self.assertEqual(self.service.start(new['run_id'])['status'],'running')

    def test_failure_is_not_success(self):
        run=self.service.start(self.create()['run_id']);rid=run['run_id'];token=run['execution_token']
        q=self.service._next_chunk(rid,token,1)[0];self.service.checkpoint(rid,token,q['pair_id'],result())
        q=self.service._next_chunk(rid,token,1)[0];self.service.checkpoint(rid,token,q['pair_id'],error='Azure failure')
        run=self.service.finish(rid,token)
        self.assertEqual(run['status'],'failed');self.assertEqual(run['completed_questions'],1)
        self.assertEqual(run['failed_questions'],1);self.assertIsNone(run['questions'][1]['result'])

    def test_scope_and_invalid_transitions(self):
        run=self.create()
        with self.assertRaises(ValueError): self.service.request_stop(run['run_id'])
        with self.assertRaises(ValueError): self.create()
        for assessment,test,candidate in [('Other','Test','C1'),('Assessment','Other','C1'),('Assessment','Test','C2')]:
            self.service.create_run(assessment,test,records(candidate))
        run=self.service.start(run['run_id'])
        with self.assertRaises(ValueError): self.service.start(run['run_id'])
        self.assertEqual(len(self.repo.get_all()),4)

    def test_malformed_storage_not_erased(self):
        self.repo.file_path.write_text('{bad')
        with self.assertRaises(ValueError): self.create()
        self.assertEqual(self.repo.file_path.read_text(),'{bad')

    def test_execute_stops_after_inflight_and_resumes_without_regrading(self):
        rid=self.create()['run_id'];calls=[]
        def grade(client,deployment,record,*args):
            calls.append(record['question_no'])
            if record['question_no']=='Q1': self.service.request_stop(rid)
            return result()
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',side_effect=grade):
            run=self.service.execute(rid)
            self.assertEqual(run['status'],'paused');self.assertEqual(calls,['Q1'])
            run=AIEvaluationRunService(self.repo).execute(rid)
        self.assertEqual(run['status'],'completed');self.assertEqual(calls,['Q1','Q2','Q3'])
        self.assertEqual(run['percentage'],100)

    def test_worker_failure_preserves_success_and_actual_counts(self):
        rid=self.create()['run_id']
        def grade(client,deployment,record,*args):
            if record['question_no']=='Q2': raise ValueError('Azure error')
            return result()
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',side_effect=grade):
            run=self.service.execute(rid)
        self.assertEqual(run['status'],'failed');self.assertEqual(run['completed_questions'],2)
        self.assertEqual(run['failed_questions'],1);self.assertEqual(run['questions'][1]['error'],'Azure error')

    def test_live_restart_and_duplicate_worker(self):
        rid=self.create()['run_id'];entered=threading.Event();release=threading.Event();failures=[]
        def grade(*args):
            entered.set()
            if not release.wait(5): raise RuntimeError('test timeout')
            return result()
        def execute():
            try: self.service.execute(rid)
            except Exception as exc: failures.append(exc)
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',side_effect=grade):
            thread=threading.Thread(target=execute);thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(ValueError): self.service.execute(rid)
                new=self.service.restart(rid)
            finally:
                release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(failures,[])
        self.assertEqual(self.service.get_run(new['run_id'])['completed_questions'],0)
        self.assertEqual(self.service.get_run(rid)['completed_questions'],1)

    def test_batch_questionwise_checkpoint_stop_and_skip_completed(self):
        rows=[r for q in range(1,4) for c in ('C1','C2') for r in [records(c)[q-1]]]
        rid=self.service.create_run('Assessment','Test',rows,candidate_scope='all',**self.ids)['run_id']
        calls=[]
        def grade(client,deployment,chunk,*args):
            calls.append([(r['candidate_id'],r['question_no']) for r in chunk])
            if chunk[0]['question_no']=='Q1': self.service.request_stop(rid)
            return [dict(result(),response_id=r['response_id'],status='completed') for r in chunk]
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_question_batch',side_effect=grade):
            paused=self.service.execute(rid)
            self.assertEqual(paused['completed_questions'],2);self.assertEqual(paused['status'],'paused')
            finished=self.service.execute(rid)
        self.assertEqual(calls,[[('C1','Q1'),('C2','Q1')],[('C1','Q2'),('C2','Q2')],[('C1','Q3'),('C2','Q3')]])
        self.assertEqual(finished['completed_questions'],6)
        self.assertEqual(set(self.service.result_rows(finished)),{'C1','C2'})

    def test_unanswered_no_azure_client(self):
        rows=records()
        for row in rows: row.update(unanswered=True,candidate_answer=None)
        rid=self.service.create_run('Assessment','Test',rows,**self.ids)['run_id']
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client') as client:
            run=self.service.execute(rid)
        client.assert_not_called()
        self.assertEqual(run['status'],'completed')
        self.assertTrue(all(q['result']['awarded_marks']==0 for q in run['questions']))

    def test_recovery_does_not_steal_live_process(self):
        run=self.service.start(self.create()['run_id']);rid=run['run_id']
        run['owner_process']='prior-process';self.repo.save(run)
        with patch.object(self.service,'_owner_alive',return_value=True):
            self.assertEqual(self.service.recover_interrupted(rid)['status'],'running')
        with patch.object(self.service,'_owner_alive',return_value=False):
            self.assertEqual(self.service.recover_interrupted(rid)['status'],'paused')

    def test_restart_write_failure_is_atomic(self):
        run=self.create();before=self.repo.file_path.read_bytes()
        with patch('backend.repositories.json_repository.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.service.restart(run['run_id'])
        self.assertEqual(self.repo.file_path.read_bytes(),before)

    def test_snapshot_isolated_and_stale_token_rejected(self):
        source=records();run=self.service.create_run('Assessment','Test',source,**self.ids)
        source[0]['candidate_answer']='Changed'
        self.assertEqual(self.service.get_run(run['run_id'])['questions'][0]['record']['candidate_answer'],'Answer')
        run=self.service.start(run['run_id']);q=self.service._next_chunk(run['run_id'],run['execution_token'],1)[0]
        with self.assertRaises(ValueError): self.service.checkpoint(run['run_id'],'old-token',q['pair_id'],result())
        self.assertEqual(self.service.get_run(run['run_id'])['completed_questions'],0)

    def test_real_workbook_prepare_and_resume_snapshot(self):
        import pandas as pd
        folder=Path(self.temp.name)
        paper=folder/'paper.xlsx';response=folder/'response.xlsx'
        rows=[{'Question No':f'Q{i}','Question':f'Question {i}','Marks':2,'Answer Key':'Reference',
               'CO':'CO1','LO':'LO1','Knowledge Type':'Conceptual','Domain':'Cognitive','RBT level':'Understand'} for i in range(1,4)]
        pd.DataFrame(rows).to_excel(paper,index=False)
        pd.DataFrame([dict(r,**{'Candidate Answer':'Answer'}) for r in rows]).to_excel(response,index=False)
        run=self.service.prepare_single('Assessment','Test','C1','Name (C1)',paper,response,**self.ids)
        self.assertEqual(run['candidate_id'],'C1');self.assertEqual(run['total_questions'],3)
        response.write_bytes(b'changed file')
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',return_value=result()):
            self.assertEqual(self.service.execute(run['run_id'])['status'],'completed')

    def test_partial_batch_success_saved_before_retry(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock
        from test_ai_questionwise import grade
        rows=records('C1',1)+records('C2',1)
        rid=self.service.create_run('Assessment','Test',rows,candidate_scope='all',**self.ids)['run_id']
        client=Mock();calls=[]
        def create(**kwargs):
            prompt=kwargs['messages'][0]['content']
            answers=json.loads(prompt.split('STUDENT ANSWER:\n',1)[1].split('\n\nMAXIMUM MARKS:',1)[0])
            calls.append(answers)
            chosen=answers[:1]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'results':[grade(a['response_id'],1) for a in chosen]})))])
        client.chat.completions.create.side_effect=create
        counts=[]
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(client,'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service.time.sleep',side_effect=lambda delay: counts.append(self.service.get_run(rid)['completed_questions'])):
            run=self.service.execute(rid)
        self.assertEqual(counts,[1]);self.assertEqual([len(c) for c in calls],[2,1])
        self.assertEqual(run['completed_questions'],2)

if __name__=='__main__': unittest.main()
