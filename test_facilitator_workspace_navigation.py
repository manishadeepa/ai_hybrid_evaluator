"""Real Reflex state events against isolated assessment/test/assignment repositories."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, AsyncMock
from backend.repositories.candidate_repository import CandidateRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService
with patch('dotenv.load_dotenv'):
    import reflex as rx
    import ai_hybrid_evaluator.state.facilitator_state as module
    import ai_hybrid_evaluator.state.admin_state as admin_module
    from ai_hybrid_evaluator.state.auth_state import AuthState


class WorkspaceNavigationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.candidates=CandidateManagementService(CandidateRepository(self.root/'candidates.json'))
        self.service=self.candidates.assessments
        self.assignments=CandidateAssignmentService(self.candidates)
        self.candidates.create_candidate({'candidate_id':'NAV-C1','name':'Candidate','email':'nav@example.com'})
        self.first=self.service.save_assessment({'name':'First assessment','facilitator_ids':['F001'],
            'facilitator_id':'F001','assigned_candidates':[],'tests':[],'status':'Draft'})
        self.second=self.service.save_assessment({'name':'Second assessment','facilitator_ids':['F001'],
            'facilitator_id':'F001','assigned_candidates':['NAV-C1'],'tests':[],'status':'Draft'})
        root=rx.State(_reflex_internal_init=True)
        self.fac=root.get_substate(tuple(module.FacilitatorState.get_full_name().split('.')))
        self.admin=root.get_substate(tuple(admin_module.AdminState.get_full_name().split('.')))
        self.auth=root.get_substate(tuple(AuthState.get_full_name().split('.')))
        self.auth.facilitator_emp_id='F001';self.auth.is_facilitator_authenticated=True
        self.admin.candidates=[{'emp_id':'NAV-C1','name':'Candidate','email':'nav@example.com'}]
        self.fac.saved_assessment_weightages={'unused':{}}
        for target,value in ((admin_module,'AssessmentService'),(module,'AssessmentService')):
            change=patch.object(target,value,return_value=self.service);change.start();self.addCleanup(change.stop)
        change=patch.object(module.FacilitatorState,'sync_assessment_weightage',new=AsyncMock());change.start();self.addCleanup(change.stop)
        change=patch.object(module.FacilitatorState,'_unmark_assessment_complete');change.start();self.addCleanup(change.stop)

    async def create_after_load(self, expected):
        await self.fac.load_persisted_assessment_workspace()
        self.assertEqual(self.fac.selected_assessment_name,expected['name'])
        await self.fac.open_add_test_modal()
        self.assertTrue(self.fac.show_add_test_modal)
        self.fac.new_test_name='New test';self.fac.new_test_date='2099-10-01'
        self.fac.new_question_type='Subjective'
        result=await self.fac.create_new_test()
        saved=self.service.get_assessment(expected['assessment_id'])
        self.assertIn('New test',saved['test_ids'],str(result))
        self.assertEqual(self.service.tests.get_test(saved['test_ids']['New test'])['assessment_id'],expected['assessment_id'])
        other=self.first if expected['assessment_id']==self.second['assessment_id'] else self.second
        self.assertNotIn('New test',self.service.get_assessment(other['assessment_id'])['test_ids'])
        if expected['assigned_candidates']:
            self.assertEqual(self.assignments.get_test_assignment('NAV-C1',saved['test_ids']['New test'])['assessment_id'],expected['assessment_id'])

    async def test_dashboard_component_accepts_canonical_id_binding(self):
        from ai_hybrid_evaluator.pages.facilitator.dashboard import facilitator_dashboard_page
        self.assertIsNotNone(facilitator_dashboard_page())

    async def test_dashboard_load_add_create(self):
        await self.fac.open_assessment(1)
        await self.create_after_load(self.second)

    async def test_filtered_dashboard_uses_clicked_assessment(self):
        self.fac.assessment_search_query='Second'
        await self.fac.open_assessment(0)
        await self.create_after_load(self.second)

    async def test_sidebar_load_add_create(self):
        await self.fac.open_assessment_by_name(self.second['name'])
        await self.create_after_load(self.second)

    async def test_legacy_empty_facilitator_list_matches_display(self):
        record=self.service.repository.get_by_id(self.second['assessment_id'])
        record['facilitator_ids']=[];self.service.repository.save(record)
        await self.fac.open_assessment_by_name(self.second['name'])
        await self.create_after_load(self.second)

    async def test_dashboard_id_survives_catalog_reordering(self):
        records=self.service.repository.get_all();self.service.repository.save_all(list(reversed(records)))
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        await self.create_after_load(self.second)

    async def test_workspace_recovers_blank_display_name_by_id(self):
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        self.fac.selected_assessment_name=''
        await self.create_after_load(self.second)

    async def test_renamed_assessment_keeps_identity(self):
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        record=self.service.get_assessment(self.second['assessment_id']);record['name']='Renamed assessment'
        renamed=self.service.save_assessment(record)
        await self.create_after_load(renamed)

    async def test_unassigned_assessment_cannot_be_opened_or_modified(self):
        self.auth.facilitator_emp_id='F002'
        event=await self.fac.open_assessment_by_id(self.second['assessment_id'])
        self.assertNotIn('/facilitator/assessment',str(event))
        self.assertEqual(self.fac.selected_assessment_id,'')
        await self.fac.open_add_test_modal();self.assertFalse(self.fac.show_add_test_modal)
        self.fac.new_test_name='Blocked';self.fac.new_test_date='2099-10-01'
        await self.fac.create_new_test();self.assertEqual(self.service.tests.repository.get_all(),[])

    async def test_workspace_index_is_relative_to_assigned_list(self):
        rows=self.service.repository.get_all();rows[0]['facilitator_ids']=['F002'];self.service.repository.save_all(rows)
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        self.assertEqual(self.fac.selected_assessment_index,0)
        await self.create_after_load(self.second)

    async def test_sidebar_test_and_tab_keep_canonical_selection(self):
        updated=self.service.add_test(self.second['assessment_id'],'Existing')
        await self.fac.open_assessment_test(self.second['name'],'Existing')
        self.assertEqual(self.fac.selected_test_name,'Existing')
        self.assertEqual(self.fac.selected_assessment_id,self.second['assessment_id'])
        await self.fac.open_assessment_tab(self.second['name'],'tests')
        await self.create_after_load(self.second)

    async def test_deleted_id_never_falls_back_to_other_assessment(self):
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        self.service.delete_assessment(self.second['assessment_id'])
        self.fac.selected_assessment_name=self.first['name']
        await self.fac.load_persisted_assessment_workspace()
        self.assertEqual(self.fac.selected_assessment_id,'');self.assertEqual(self.fac.selected_assessment_name,'')
        self.fac.new_test_name='Blocked';self.fac.new_test_date='2099-10-01'
        await self.fac.create_new_test();self.assertEqual(self.service.tests.repository.get_all(),[])

    async def test_missing_session_does_not_show_default_facilitator_records(self):
        self.auth.facilitator_emp_id='';self.auth.is_facilitator_authenticated=False
        await self.fac.load_persisted_assessment_workspace()
        self.assertEqual(await self.fac.my_assessments,[])

    async def test_expired_session_requires_signin_without_creating_test(self):
        await self.fac.open_assessment_by_id(self.second['assessment_id'])
        self.auth.facilitator_emp_id=''
        event=await self.fac.load_persisted_assessment_workspace()
        self.assertIn('/signin',str(event))
        self.assertEqual(self.fac.selected_assessment_id,'')
        self.fac.new_test_name='Blocked';self.fac.new_test_date='2099-10-01'
        self.fac.new_question_type='Subjective'
        event=await self.fac.create_new_test()
        self.assertIn('/signin',str(event))
        self.assertEqual(self.service.tests.repository.get_all(),[])

    async def test_invalid_open_does_not_navigate_to_empty_workspace(self):
        event=await self.fac.open_assessment(99)
        self.assertNotIn('/facilitator/assessment',str(event))
        await self.fac.open_add_test_modal()
        self.assertFalse(self.fac.show_add_test_modal)
        self.fac.new_test_name='Blocked';self.fac.new_test_date='2099-10-01'
        await self.fac.create_new_test()
        self.assertEqual(self.service.tests.repository.get_all(),[])

if __name__=='__main__': unittest.main()
