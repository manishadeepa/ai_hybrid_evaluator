"""Assessment/test persistence checks use temporary JSON only; no live app data."""
import ast
import asyncio
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.repositories.json_repository import JSONRepository
from backend.services.assessment_service import AssessmentService
from backend.services.test_service import TestService


def sample(name='Quality'):
    return {'name': name, 'facilitator_ids': ['F001'], 'facilitator_names': ['Facilitator'],
            'facilitator_id': 'F001', 'facilitator_name': 'Facilitator',
            'assigned_candidates': ['C1'], 'status': 'Scheduled', 'approval_status': 'approved',
            'tests': ['Formative 1', 'Formative 2'], 'final_test': 'Summative Test',
            'test_dates': {'Formative 1': 'first date', 'Formative 2': 'second date'},
            'test_descriptions': {'Formative 2': 'second description'},
            'question_papers': {'Formative 1': 'first.xlsx', 'Formative 2': 'second.xlsx'}}


def extract_methods(path, class_name, names, namespace):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return type(class_name + 'Harness', (), {name: namespace[name] for name in names})


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.assessments = AssessmentRepository(self.folder / 'assessments.json')
        self.tests = TestRepository(self.folder / 'tests.json')
        self.service = AssessmentService(self.assessments, TestService(self.tests))

    def test_create_reload_update_ids_and_no_duplicates(self):
        saved = self.service.save_assessment(sample())
        again = self.service.save_assessment(saved)
        self.assertEqual(saved['assessment_id'], again['assessment_id'])
        self.assertEqual(saved['test_ids'], again['test_ids'])
        self.assertEqual(len(self.assessments.get_all()), 1)
        self.assertEqual(len(self.tests.get_all()), 3)
        fresh = AssessmentService(AssessmentRepository(self.folder/'assessments.json'), TestService(TestRepository(self.folder/'tests.json')))
        self.assertEqual(fresh.load_assessments(), [saved])
        saved['name'] = 'Renamed'
        saved['assigned_candidates'] = ['C2']
        saved['test_dates']['Formative 2'] = 'updated'
        updated = fresh.save_assessment(saved)
        self.assertEqual(updated['assessment_id'], again['assessment_id'])
        self.assertEqual(updated['test_ids'], again['test_ids'])
        self.assertEqual(fresh.load_assessments()[0]['assigned_candidates'], ['C2'])

    def test_test_creation_and_assessment_isolation(self):
        a = self.service.save_assessment(sample())
        b = self.service.save_assessment(sample('Other'))
        a['tests'].append('Formative 3')
        a['test_dates']['Formative 3'] = 'new date'
        a = self.service.save_assessment(a)
        self.assertEqual(len(self.service.tests.get_tests(a['assessment_id'])), 4)
        self.assertEqual(len(self.service.tests.get_tests(b['assessment_id'])), 3)
        self.assertNotEqual(a['test_ids']['Formative 1'], b['test_ids']['Formative 1'])

    def test_renumber_preserves_identity_and_question_paper(self):
        a = self.service.save_assessment(sample())
        survivor = a['test_ids']['Formative 2']
        updated = self.service.delete_test(a['assessment_id'], a['test_ids']['Formative 1'], renumber=True)
        self.assertEqual(updated['tests'], ['Formative 1'])
        self.assertEqual(updated['test_ids']['Formative 1'], survivor)
        self.assertEqual(updated['test_dates']['Formative 1'], 'second date')
        self.assertEqual(updated['test_descriptions']['Formative 1'], 'second description')
        self.assertEqual(updated['question_papers']['Formative 1'], 'second.xlsx')
        self.assertEqual(self.service.load_assessments()[0], updated)

    def test_delete_assessment_cascades_only_its_tests(self):
        a = self.service.save_assessment(sample())
        b = self.service.save_assessment(sample('Other'))
        self.service.delete_assessment(a['assessment_id'])
        self.assertEqual(self.service.load_assessments(), [b])
        self.assertTrue(all(r['assessment_id'] == b['assessment_id'] for r in self.tests.get_all()))

    def test_bootstrap_once_and_empty_stays_empty(self):
        a = self.service.load_or_bootstrap([sample()])[0]
        self.assertEqual(self.service.load_or_bootstrap([sample('Do not import')])[0], a)
        self.service.delete_assessment(a['assessment_id'])
        self.assertEqual(self.service.load_or_bootstrap([sample()]), [])

    def test_unrelated_json_unchanged_and_existing_json_readable(self):
        path = self.folder/'manual_evaluations.json'
        path.write_text('[{"candidate_id":"C1","questions":[]}]', encoding='utf-8')
        before = path.read_bytes()
        self.service.save_assessment(sample())
        self.assertEqual(JSONRepository(path).get_all()[0]['candidate_id'], 'C1')
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('tests', self.assessments.get_all()[0])
        self.assertIn('assessment_id', self.tests.get_all()[0])

    def test_question_paper_removal_persists(self):
        a = self.service.save_assessment(sample())
        identity = a['test_ids']['Formative 1']
        a['question_papers'].pop('Formative 1')
        self.service.save_assessment(a)
        loaded = self.service.load_assessments()[0]
        self.assertNotIn('Formative 1', loaded['question_papers'])
        self.assertEqual(loaded['test_ids']['Formative 1'], identity)

    def test_invalid_edit_does_not_replace_saved_data(self):
        a = self.service.save_assessment(sample())
        before = self.tests.get_all()
        a['tests'].append('Formative 1')
        with self.assertRaises(ValueError):
            self.service.save_assessment(a)
        self.assertEqual(self.tests.get_all(), before)

    def harnesses(self):
        toast = SimpleNamespace(success=lambda *args, **kw: args, error=lambda *args, **kw: args, info=lambda *args, **kw: args)
        ns = {'AssessmentService': lambda: self.service, 'rx': SimpleNamespace(toast=toast), 'datetime': datetime}
        names = {'_apply_assessment_records', '_load_persisted_assessments', 'load_persisted_assessments', '_persist_assessment_record', '_add_assessment_test',
                 'add_assessment', 'save_edit_assessment', 'confirm_delete_assessment',
                 'add_test_to_selected_assessment', 'remove_test_from_selected_assessment', 'set_test_date'}
        Admin = extract_methods('ai_hybrid_evaluator/state/admin_state.py', 'AdminState', names, ns)
        admin = Admin()
        admin.assessments = [sample()]
        admin.test_question_papers = {}
        admin.candidates = [{'emp_id':'C1','name':'One'}, {'emp_id':'C2','name':'Two'}]
        admin.set_show_add_assessment = lambda value: None
        admin.set_show_edit_assessment = lambda value: None
        admin.set_show_delete_assessment = lambda value: None
        ns['AdminState'] = Admin
        ns['AuthState'] = type('AuthHarness', (), {})
        auth = SimpleNamespace(facilitator_emp_id='F001')
        from backend.repositories.candidate_repository import CandidateRepository
        from backend.services.candidate_management_service import CandidateManagementService
        from backend.services.candidate_assignment_service import CandidateAssignmentService
        candidates = CandidateManagementService(CandidateRepository(self.service.repository.file_path.parent/'candidates.json'), assessments=self.service)
        for cid in ('C1', 'C2'):
            candidates.create_candidate({'candidate_id':cid,'name':cid,'email':cid+'@example.com'})
        ns['CandidateAssignmentService'] = lambda: CandidateAssignmentService(candidates)
        fnames = {'_workspace_assessment', 'load_persisted_assessment_workspace', 'create_new_test', 'facilitator_remove_test', 'remove_test_question_paper'}
        Fac = extract_methods('ai_hybrid_evaluator/state/facilitator_state.py', 'FacilitatorState', fnames, ns)
        fac = Fac()
        fac.question_papers = {}
        fac.selected_assessment_id = ''
        async def get_state(cls):
            return auth if cls is ns['AuthState'] else admin
        fac.get_state = get_state
        fac._unmark_assessment_complete = lambda name: None
        async def sync_weightage(name):
            return None
        fac.sync_assessment_weightage = sync_weightage
        fac.selected_assessment_name = 'Quality'
        fac.selected_test_name = 'Formative 1'
        return admin, fac

    def test_bootstrap_preserves_facilitator_only_question_paper(self):
        admin, fac = self.harnesses()
        admin.assessments[0]['question_papers'] = {}
        fac.question_papers = {'Quality': {'Formative 1': 'legacy.xlsx'}}
        asyncio.run(fac.load_persisted_assessment_workspace())
        self.assertEqual(self.service.load_assessments()[0]['question_papers']['Formative 1'], 'legacy.xlsx')
        fac.question_papers = {'Quality': {'Formative 1': 'stale.xlsx'}}
        asyncio.run(fac.load_persisted_assessment_workspace())
        self.assertEqual(fac.question_papers['Quality']['Formative 1'], 'legacy.xlsx')

    def test_admin_state_creation_edit_deletion(self):
        admin, fac = self.harnesses()
        admin.load_persisted_assessments()
        admin.facilitators = [{'emp_id':'F001','name':'Facilitator'}]
        admin.new_assessment_name='Created'
        admin.new_assessment_date='date'
        admin.new_assessment_facilitator_ids=['F001']
        admin.new_assessment_candidate_ids=['C1']
        admin.new_assessment_status='Draft'
        admin.add_assessment()
        self.assertEqual(len(self.service.load_assessments()), 2)
        admin.edit_assessment_index=1
        identity=admin.assessments[1]['assessment_id']
        admin.edit_assessment_name='Edited'
        admin.edit_assessment_date='new date'
        admin.edit_assessment_facilitator_ids=['F001']
        admin.edit_assessment_candidate_ids=['C2']
        admin.edit_assessment_status='Scheduled'
        admin.save_edit_assessment()
        self.assertEqual(self.service.load_assessments()[1]['assessment_id'], identity)
        self.assertEqual(self.service.load_assessments()[1]['name'], 'Edited')
        admin.delete_assessment_index=1
        admin.confirm_delete_assessment()
        self.assertEqual(len(self.service.load_assessments()),1)

    def test_state_restore_facilitator_create_remove_and_qp(self):
        admin, fac = self.harnesses()
        asyncio.run(fac.load_persisted_assessment_workspace())
        self.assertEqual(fac.question_papers['Quality']['Formative 2'],'second.xlsx')
        fac.new_test_name='Formative 3'
        fac.new_test_date='2026-09-18'
        fac.new_test_type='Formative'
        fac.new_test_description='New test'
        asyncio.run(fac.create_new_test())
        saved=self.service.load_assessments()[0]
        self.assertIn('Formative 3', saved['test_ids'])
        self.assertEqual(saved['test_descriptions']['Formative 3'],'New test')
        admin.assessments=[]
        fac.question_papers={}
        asyncio.run(fac.load_persisted_assessment_workspace())
        self.assertIn('Formative 3',admin.assessments[0]['tests'])
        asyncio.run(fac.remove_test_question_paper('Formative 2'))
        self.assertNotIn('Formative 2',self.service.load_assessments()[0]['question_papers'])
        asyncio.run(fac.facilitator_remove_test('Formative 3'))
        self.assertNotIn('Formative 3',self.service.load_assessments()[0]['tests'])

    def test_admin_renumber_event_preserves_qp(self):
        admin, fac=self.harnesses()
        admin.load_persisted_assessments()
        survivor=admin.assessments[0]['test_ids']['Formative 2']
        admin.selected_tests_assessment_index=0
        admin.remove_test_from_selected_assessment('Formative 1')
        self.assertEqual(admin.assessments[0]['test_ids']['Formative 1'],survivor)
        self.assertEqual(admin.test_question_papers['Quality__Formative 1'],'second.xlsx')
        admin.add_test_to_selected_assessment()
        admin.set_test_date('Formative 2','2026-09-21')
        self.assertEqual(self.service.load_assessments()[0]['test_dates']['Formative 2'],'2026-09-21')


    def test_invalid_form_assignment_is_reported_without_write(self):
        admin, fac = self.harnesses()
        admin.load_persisted_assessments()
        admin.facilitators = [{'emp_id':'F001','name':'Facilitator'}]
        admin.new_assessment_name='Invalid'
        admin.new_assessment_date=''
        admin.new_assessment_facilitator_ids=['F001','missing']
        admin.new_assessment_candidate_ids=['C1']
        admin.new_assessment_status='Draft'
        before=self.assessments.file_path.read_bytes()
        admin.add_assessment()
        self.assertIn('facilitator',admin.assessment_form_error)
        self.assertEqual(self.assessments.file_path.read_bytes(),before)
        admin.new_assessment_facilitator_ids=['F001']
        admin.new_assessment_candidate_ids=['missing']
        admin.add_assessment()
        self.assertIn('candidate',admin.assessment_form_error)
        self.assertEqual(self.assessments.file_path.read_bytes(),before)

if __name__ == '__main__':
    unittest.main()
