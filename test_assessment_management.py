"""Assessment milestones: isolated temporary JSON, no Azure or live data writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.repositories.json_repository import JSONRepository
from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.services.assessment_service import AssessmentService
from backend.services.test_service import TestService

class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.repo = AssessmentRepository(self.folder/'assessments.json')
        self.tests = TestRepository(self.folder/'tests.json')
        self.facilitators = [{'emp_id':'F1','name':'First'}, {'emp_id':'F2','name':'Second'}]
        self.candidates = [{'emp_id':'C1','name':'One'}, {'emp_id':'C2','name':'Two'}]
        self.service = AssessmentService(self.repo, TestService(self.tests),
            facilitator_catalog=lambda: self.facilitators, candidate_catalog=lambda: self.candidates)

    def create(self, name='Assessment'):
        return self.service.create_assessment({'name': name, 'status': 'Draft',
            'description': 'keep', 'tests': ['Formative 1'], 'test_dates': {'Formative 1': 'legacy date'},
            'question_papers': {'Formative 1': 'paper.xlsx'}})

    def test_m1_crud_partial_update_reload_delete(self):
        a=self.create(); aid=a['assessment_id']
        b=self.create('Other')
        fresh=AssessmentService(AssessmentRepository(self.repo.file_path), TestService(TestRepository(self.tests.file_path)))
        self.assertEqual(fresh.get_assessment(aid),a)
        updated=fresh.update_assessment(aid,{'name':'Renamed'})
        self.assertEqual(updated['description'],'keep')
        self.assertEqual(updated['test_ids'],a['test_ids'])
        self.assertEqual(updated['question_papers'],a['question_papers'])
        self.assertTrue(fresh.delete_assessment(aid))
        self.assertFalse(fresh.delete_assessment(aid))
        self.assertEqual(fresh.load_assessments(),[b])
        with self.assertRaises(ValueError): fresh.get_assessment(aid)

    def test_m1_invalid_operations_do_not_erase(self):
        a=self.create(); before=self.repo.file_path.read_bytes()
        for data in ({'name':''},{'name':' assessment '},{'name':'Assessment'}):
            with self.assertRaises(ValueError): self.service.create_assessment(data)
        for identity in ('',None,'missing'):
            with self.assertRaises(ValueError): self.service.update_assessment(identity,{'name':'x'})
        self.assertEqual(self.repo.file_path.read_bytes(),before)
        with self.assertRaises(ValueError): self.service.update_assessment(a['assessment_id'],{'assessment_id':'other'})

    def test_m1_bad_json_preserved(self):
        for content in ('','{broken','{}','[1]','[{"assessment_id":"x"},{"assessment_id":"x"}]'):
            self.repo.file_path.write_text(content)
            with self.assertRaises(ValueError): self.service.load_assessments()
            self.assertEqual(self.repo.file_path.read_text(),content)

    def test_m1_atomic_write_failure_keeps_original(self):
        self.create(); before=self.repo.file_path.read_bytes()
        with patch('backend.repositories.json_repository.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.repo.save_all([])
        self.assertEqual(self.repo.file_path.read_bytes(),before)
        self.assertEqual(list(self.folder.glob('*.tmp')),[])

    def test_m2_assignment_aliases_and_isolation(self):
        a=self.create(); b=self.create('Other'); aid=a['assessment_id']
        self.service.assign_facilitator(aid,'F1')
        saved=self.service.assign_facilitator(aid,'F2')
        self.assertEqual(saved['facilitator_names'],['First','Second'])
        self.assertEqual(saved['description'],'keep')
        saved=self.service.remove_facilitator(aid,'F1')
        self.assertEqual(saved['facilitator_id'],'F2')
        self.assertEqual(saved['facilitator_name'],'Second')
        self.assertNotIn('F1',saved['facilitator_approvals'])
        self.assertEqual(self.service.list_facilitators(b['assessment_id']),[])
        self.assertEqual(self.service.list_facilitators(aid),[{'emp_id':'F2','name':'Second'}])

    def test_m2_invalid_and_duplicate_assignment(self):
        aid=self.create()['assessment_id'];self.service.assign_facilitator(aid,'F1')
        before=self.repo.file_path.read_bytes()
        for identity in ('F1','missing',''):
            with self.assertRaises(ValueError): self.service.assign_facilitator(aid,identity)
        with self.assertRaises(ValueError): self.service.assign_facilitator('missing','F1')
        with self.assertRaises(ValueError): self.service.remove_facilitator(aid,'F2')
        self.assertEqual(self.repo.file_path.read_bytes(),before)

    def test_m3_candidate_assignments_persist_and_isolate(self):
        aid=self.create()['assessment_id']; other=self.create('Other')['assessment_id']
        self.service.assign_candidate(aid,'C1'); self.service.assign_candidate(aid,'C2')
        self.assertEqual(self.service.list_candidates(aid),['C1','C2'])
        self.assertEqual(self.service.list_candidates(other),[])
        self.service.remove_candidate(aid,'C1')
        fresh=AssessmentService(self.repo,TestService(self.tests))
        self.assertEqual(fresh.list_candidates(aid),['C2'])
        self.assertEqual(fresh.get_assessment(aid)['description'],'keep')

    def test_m3_invalid_candidate_references_and_duplicates(self):
        aid=self.create()['assessment_id']; self.service.assign_candidate(aid,'C1')
        before=self.repo.file_path.read_bytes()
        for identity in ('C1','missing',''):
            with self.assertRaises(ValueError): self.service.assign_candidate(aid,identity)
        with self.assertRaises(ValueError): self.service.assign_candidate('missing','C1')
        with self.assertRaises(ValueError): self.service.create_assessment({'name':'Bad','assigned_candidates':['missing']})
        with self.assertRaises(ValueError): self.service.update_assessment(aid,{'assigned_candidates':['C1','C1']})
        self.assertEqual(self.repo.file_path.read_bytes(),before)

    def test_m4_lifecycle_dates_and_status_compatibility(self):
        aid=self.create()['assessment_id']
        saved=self.service.update_lifecycle(aid,start_date='19 Sep 2026',end_date='2026-09-21',status='Scheduled')
        self.assertEqual(saved['start_date'],'2026-09-19')
        self.assertEqual(saved['description'],'keep')
        for status in ('Draft','Scheduled','Active','Completed'):
            self.assertEqual(self.service.update_lifecycle(aid,status=status)['status'],status)
        self.assertEqual(self.service.get_assessment(aid)['end_date'],'2026-09-21')

    def test_m4_invalid_dates_leave_storage_unchanged(self):
        aid=self.create()['assessment_id']
        self.service.update_lifecycle(aid,start_date='2026-09-19',end_date='2026-09-21')
        before=self.repo.file_path.read_bytes()
        for changes in ({'start_date':'2026-02-30'},{'end_date':'2026-09-18'}, {'status':'Done'}, {'end_date':None}):
            with self.assertRaises(ValueError): self.service.update_lifecycle(aid,**changes)
        self.assertEqual(self.repo.file_path.read_bytes(),before)

    def test_m5_test_relationships_and_scope(self):
        aid=self.create()['assessment_id']; bid=self.create('Other')['assessment_id']
        saved=self.service.add_test(aid,'Formative 2',description='Second')
        tid=saved['test_ids']['Formative 2']
        self.assertEqual(self.service.get_test(aid,tid)['description'],'Second')
        self.assertEqual(len(self.service.list_tests(aid)),2)
        self.assertEqual(len(self.service.list_tests(bid)),1)
        with self.assertRaises(ValueError): self.service.get_test(bid,tid)
        with self.assertRaises(ValueError): self.service.delete_test(bid,tid)
        self.service.delete_test(aid,tid)
        with self.assertRaises(ValueError): self.service.get_test(aid,tid)
        self.assertEqual(len(self.service.list_tests(aid)),1)

    def test_m5_invalid_duplicate_relationships(self):
        aid=self.create()['assessment_id'];before=self.tests.file_path.read_bytes()
        with self.assertRaises(ValueError): self.service.add_test(aid,'formative 1')
        with self.assertRaises(ValueError): self.service.add_test('missing','Test')
        with self.assertRaises(ValueError): self.service.delete_test(aid,'missing')
        with self.assertRaises(ValueError): self.service.get_test(aid,'')
        self.assertEqual(self.tests.file_path.read_bytes(),before)

    def test_m6_progress_scoping_partial_and_manual(self):
        from backend.services.assessment_progress_service import AssessmentProgressService
        aid=self.create()['assessment_id']
        self.service.assign_candidate(aid,'C1'); self.service.assign_candidate(aid,'C2')
        lookups=[]
        def response(**identity):
            lookups.append(identity)
            return {'responses':[{'q_no':'Q1'}]} if identity['candidate_id']=='C1' else {}
        progress=AssessmentProgressService(self.service,response,lambda:[])
        partial={'candidate_id':'C1','assessment_name':'Assessment','test_name':'Formative 1','status':'partial','questions':[{'status':'failed'}]}
        data=progress.get_progress(aid,{'one':partial,'other':dict(partial,assessment_name='Other',status='completed')})
        self.assertEqual(data['submitted_candidates'],1)
        self.assertEqual(data['evaluated_candidates'],0)
        self.assertEqual(data['pending_candidates'],2)
        self.assertEqual(data['incomplete_candidates'],1)
        self.assertEqual(data['progress_percentage'],0)
        self.assertFalse(data['complete'])
        self.assertTrue(all(r['assessment_name']=='Assessment' for r in lookups))
        completed=dict(partial,status='completed',questions=[{}])
        data=progress.get_progress(aid,{'one':completed})
        self.assertEqual(data['progress_percentage'],50)
        self.assertEqual(data['evaluated_candidates'],1)
        progress.manual_loader=lambda:[dict(completed,evaluation_type='manual')]
        data=progress.get_progress(aid,{'one':partial})
        self.assertEqual(data['ambiguous_candidate_tests'],1)
        self.assertIsNone(data['complete'])
        self.assertIsNone(data['progress_percentage'])

    def test_m6_complete_empty_and_unscoped(self):
        from backend.services.assessment_progress_service import AssessmentProgressService
        aid=self.create()['assessment_id']
        progress=AssessmentProgressService(self.service,lambda **kw:{'responses':[{}]},lambda:[])
        self.assertFalse(progress.get_progress(aid)['complete'])
        self.service.assign_candidate(aid,'C1')
        record={'candidate_id':'C1','assessment_name':'Assessment','test_name':'Formative 1','status':'completed','questions':[{}]}
        self.assertTrue(progress.get_progress(aid,{'key':record})['complete'])
        self.assertEqual(progress.get_progress(aid,{'key':record})['progress_percentage'],100)
        self.assertFalse(progress.get_progress(aid,{'C1:Formative 1':{'questions':[{}]}})['complete'])
        progress.manual_loader=lambda:[dict(record,evaluation_type='manual')]
        self.assertTrue(progress.get_progress(aid)['complete'])

    def test_failure_between_stores_rolls_back_tests(self):
        a=self.create(); before=self.tests.file_path.read_bytes()
        with patch.object(self.repo,'save',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.service.add_test(a['assessment_id'],'Formative 2')
        self.assertEqual(self.tests.file_path.read_bytes(),before)
        self.assertEqual(self.service.get_assessment(a['assessment_id']),a)
        with patch.object(self.repo,'delete',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.service.delete_assessment(a['assessment_id'])
        self.assertEqual(self.tests.file_path.read_bytes(),before)

    def test_partial_metadata_update_and_invalid_types(self):
        aid=self.create()['assessment_id']
        self.service.add_test(aid,'Formative 2',date='2099-09-20')
        saved=self.service.update_assessment(aid,{'test_dates':{'Formative 1':'changed'}})
        self.assertEqual(saved['test_dates']['Formative 2'],'2099-09-20')
        before=self.repo.file_path.read_bytes()
        for data in ({'tests':None},{'status':{}},{'test_dates':[]},{'final_test':7},{'description':object()}):
            with self.assertRaises(ValueError): self.service.update_assessment(aid,data)
        self.assertEqual(self.repo.file_path.read_bytes(),before)

    def test_manual_persistence_regression_isolated(self):
        from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository
        from backend.services.manual_evaluation_service import ManualEvaluationService
        repo=object.__new__(ManualEvaluationRepository)
        repo.storage=JSONRepository(self.folder/'manual.json')
        service=ManualEvaluationService(repo)
        row={'q_no':'Q1','question':'Question','response':'Answer','max_marks':4,'awarded_marks':3,'justification':'Reason'}
        result=service.evaluate_and_save('C1','Assessment','Formative 1',[row])
        self.assertEqual(result['percentage'],75)
        self.assertEqual(service.get_evaluation('C1','Assessment','Formative 1')['total_marks'],3)
        self.assertIsNone(service.get_evaluation('C1','Other','Formative 1'))
        with self.assertRaises(ValueError): service.evaluate_and_save('C1','Assessment','Formative 1',[dict(row,awarded_marks=5)])
        self.assertEqual(service.get_evaluation('C1','Assessment','Formative 1'),result)

if __name__ == '__main__': unittest.main()
