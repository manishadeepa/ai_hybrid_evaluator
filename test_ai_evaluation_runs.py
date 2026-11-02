"""Offline lifecycle regressions, isolated run persistence."""
import tempfile
import unittest
import threading
from unittest.mock import patch
from pathlib import Path
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.services.ai_evaluation_run_service import AIEvaluationRunService
from backend.services import ai_evaluation_run_service as run_service_module


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
        from backend.services.ai_connection_service import AIConnectionService
        config_patch = patch.object(
            AIConnectionService,
            "validate_active_configuration",
            return_value=None,
        )
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.repo=AIEvaluationRunRepository(Path(self.temp.name)/'runs.json')
        self.service=AIEvaluationRunService(self.repo)
        from backend.services.assessment_service import AssessmentService
        from backend.repositories.assessment_repository import AssessmentRepository
        assessments=AssessmentService(AssessmentRepository(Path(self.temp.name)/'assessments.json'), self.service.tests)
        assessment=assessments.create_assessment({'name':'Assessment'})
        self.actor={'facilitator_id':'F001','role':'facilitator'}
        for name in ('create_run','request_stop','recover_interrupted','restart','start','_next_chunk',
                     'checkpoint','finish','execute','prepare_single','prepare_batch'):
            bound=getattr(self.service,name)
            def owner_call(*args,_bound=bound,**kwargs):
                kwargs.setdefault('facilitator_id','F001')
                kwargs.setdefault('role','facilitator')
                return _bound(*args,**kwargs)
            setattr(self.service,name,owner_call)
        test=self.service.tests.create_test(assessment['assessment_id'], {'test_name':'Test','test_type':'subjective'},created_by='F001')
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
        self.service.create_run('Assessment','Test',records('C2'),**self.ids)
        run=self.service.start(run['run_id'])
        with self.assertRaises(ValueError): self.service.start(run['run_id'])
        self.assertEqual(len(self.repo.get_all()),2)

    def test_only_test_creator_can_mutate_run_directly(self):
        run = self.create()
        service = AIEvaluationRunService(self.repo, tests=self.service.tests)
        for operation in (
            lambda: service.start(run['run_id'], facilitator_id='F002', role='facilitator'),
            lambda: service.request_stop(run['run_id'], facilitator_id='F002', role='facilitator'),
            lambda: service.restart(run['run_id'], facilitator_id='F002', role='facilitator'),
            lambda: service.execute(run['run_id'], facilitator_id='F002', role='facilitator'),
            lambda: service.checkpoint(
                run['run_id'], 'stale-token', 'pair',
                result(), facilitator_id='F002', role='facilitator',
            ),
            lambda: service.finish(
                run['run_id'], 'stale-token',
                facilitator_id='F002', role='facilitator',
            ),
            lambda: service.update_review_result(
                self.ids['test_id'], self.ids['assessment_id'], 'C1', 'Q1',
                awarded_marks=1, facilitator_id='F002', role='facilitator',
            ),
        ):
            with self.assertRaisesRegex(ValueError, "Only the facilitator who created this test"):
                operation()
        self.assertEqual(service.get_run(run['run_id']), run)

    def test_unknown_owner_cannot_create_evaluation_run(self):
        unknown = self.service.tests.create_test(
            self.ids['assessment_id'],
            {'test_name': 'Legacy'},
        )
        with self.assertRaisesRegex(ValueError, 'creator is unknown'):
            self.service.create_run(
                'Assessment', 'Legacy', records(),
                assessment_id=self.ids['assessment_id'],
                test_id=unknown['test_id'],
            )

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
            run=self.service.execute(rid)
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
        self.assertEqual(run['failed_questions'],1)
        self.assertEqual(
            run['questions'][1]['error'],
            "AI evaluation request failed (ValueError). Check Admin Settings and try again.",
        )

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
        rid=self.service.create_run('Assessment','Test',rows,candidate_scope='all',
                                    labels={'C1':'Name C1','C2':'Name C2'},**self.ids)['run_id']
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

    def test_objective_test_is_scored_locally_without_ai_connection(self):
        from backend.services.ai_connection_service import AIConnectionService
        row=records(count=1)[0]
        row.update(
            question_no='Q1',
            question='Select the correct answer.\nA) Alpha\nB) Beta\nC) Gamma\nD) Delta',
            candidate_answer='A',
            answer_key='A',
            question_type='objective',
        )
        rid=self.service.create_run('Assessment','Test',[row],**self.ids)['run_id']
        with patch.object(self.service,'_canonical_test',return_value={'test_type':'objective'}), \
             patch.object(self.service,'_validate_submission_snapshot',return_value={}), \
             patch.object(AIConnectionService,'validate_active_configuration') as configuration, \
             patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client') as client:
            run=self.service.execute(rid)
        configuration.assert_not_called()
        client.assert_not_called()
        self.assertEqual(run['status'],'completed')
        self.assertEqual(run['questions'][0]['result']['awarded_marks'],2)
        self.assertEqual(run['questions'][0]['result']['answer_status'],'Correct')

    def test_hybrid_routes_objective_locally_and_subjective_through_ai(self):
        objective = records(count=1)[0]
        objective.update(
            question_no='Q1',
            question='Select one.\nA) Alpha\nB) Beta\nC) Gamma\nD) Delta',
            answer_key='B',
            question_type='objective',
        )
        subjective = records(count=1)[0]
        subjective.update(question_no='Q2', question_type='subjective')
        rid=self.service.create_run(
            'Assessment','Test',[objective,subjective],**self.ids
        )['run_id']
        with patch.object(self.service,'_canonical_test',return_value={'test_type':'mixed'}), \
             patch.object(self.service,'_validate_submission_snapshot',return_value={}), \
             patch.object(self.service,'_validate_ai_configuration') as configuration, \
             patch.object(
                 run_service_module,
                 '_evaluate_objective_locally',
                 return_value=dict(result(),awarded_marks=2,answer_status='Correct'),
             ) as local_grade, \
             patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',
                   return_value=(object(),'deployment')) as client, \
             patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',
                   return_value=dict(result(),awarded_marks=1)) as ai_grade:
            run=self.service.execute(rid)
        configuration.assert_called_once()
        local_grade.assert_called_once()
        client.assert_called_once()
        ai_grade.assert_called_once()
        self.assertEqual(run['status'],'completed')
        self.assertEqual(
            [question['result']['awarded_marks'] for question in run['questions']],
            [2, 1],
        )

    def test_subjective_missing_admin_configuration_is_actionable(self):
        from backend.services.ai_connection_service import (
            AIConnectionService,
            AI_EVALUATION_NOT_CONFIGURED,
        )
        row=records(count=1)[0]
        row['question_type']='subjective'
        run=self.service.create_run('Assessment','Test',[row],**self.ids)
        with patch.object(
            AIConnectionService,
            'validate_active_configuration',
            side_effect=ValueError(AI_EVALUATION_NOT_CONFIGURED),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "AI evaluation is not configured. Please contact an administrator to check Admin Settings.",
            ):
                self.service.execute(run['run_id'])
        self.assertEqual(self.service.get_run(run['run_id'])['status'],'idle')

    def test_recovery_does_not_steal_live_process(self):
        run=self.service.start(self.create()['run_id']);rid=run['run_id']
        run['owner_process']='prior-process';self.repo.save(run,**self.actor)
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

        # Register the workbook through the canonical question-paper service.
        from backend.services.question_paper_service import QuestionPaperService
        papers = QuestionPaperService(self.service.tests)
        canonical_paper = papers.import_upload(
            self.ids['assessment_id'],
            self.ids['test_id'],
            'paper.xlsx',
            paper.read_bytes(),
        )

        run=self.service.prepare_single(
            'Assessment',
            'Test',
            'C1',
            'Name (C1)',
            papers.upload_dir / canonical_paper['filename'],
            response,
            **self.ids,
        )
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
        rid=self.service.create_run('Assessment','Test',rows,candidate_scope='all',
                                    labels={'C1':'Name C1','C2':'Name C2'},**self.ids)['run_id']
        client=Mock();calls=[]
        def create(**kwargs):
            prompt=kwargs['messages'][0]['content']
            answers=json.loads(prompt.split('STUDENT ANSWER:\n',1)[1].split('\n\nMAXIMUM MARKS:',1)[0])
            calls.append(answers)
            chosen=answers[:1]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'results':[grade(a['response_id'],1) for a in chosen]})))])
        client.chat.completions.create.side_effect=create
        counts=[]
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(client,'deployment')), patch('ai_hybrid_evaluator.services.ai_evaluation_service.time.sleep',side_effect=lambda delay: counts.append(self.service.get_run(rid)['completed_questions']) if delay >= 1 else None):
            run=self.service.execute(rid)
        self.assertEqual(counts,[1]);self.assertEqual([len(c) for c in calls],[2,1])
        self.assertEqual(run['completed_questions'],2)

if __name__=='__main__': unittest.main()
