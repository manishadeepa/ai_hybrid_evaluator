"""Report integration tests use temporary persisted results, never live stores or Azure."""
import unittest
from copy import deepcopy
from unittest.mock import patch
import test_evaluation_result_management as fixtures
from backend.services.report_service import ReportService
from backend.services.report_pdf import render_report_pdf


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationResultTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.service = ReportService(self.f.service)
        self.aid, self.tid = self.f.key[1:]

    def build(self, tid=None, cid=None, aid=None):
        return self.service.build(aid or self.aid, tid or self.tid, cid, admin=True)

    def test_formative_tests_are_separate(self):
        self.f.manual_result(test='Formative 1'); self.f.manual_result(test='Formative 2')
        for name in ('Formative 1', 'Formative 2'):
            tid = self.f.a['test_ids'][name]
            report = self.build(tid)
            self.assertEqual(report['test_name'], name)
            self.assertEqual({r['test_id'] for r in report['candidates']}, {tid})
            self.assertEqual(report['test_category'], 'Formative')

    def test_summative_is_separate(self):
        a = self.f.candidates.assessments.update_assessment(self.aid, {'final_test': 'Summative 1'})
        self.f.manual_result(); self.f.manual_result(test='Summative 1')
        report = self.build(a['test_ids']['Summative 1'])
        self.assertEqual(report['test_category'], 'Summative')
        self.assertEqual(len(report['candidates']), 1)
        self.assertEqual(report['candidates'][0]['test_name'], 'Summative 1')

    def test_same_test_name_other_assessment(self):
        self.f.manual_result(); self.f.manual_result(assessment='B')
        report = self.build()
        self.assertEqual({r['assessment_id'] for r in report['candidates']}, {self.aid})
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            self.build(self.f.b['test_ids']['Formative 1'])
        with self.assertRaises(ValueError): self.build(aid='A')
        with self.assertRaises(ValueError): self.build(tid='Formative 1')

    def test_candidate_identity_not_display_name(self):
        self.f.manual_result('C1'); self.f.manual_result('C2')
        rows = self.build(cid='C2')['candidates']
        self.assertEqual([r['candidate_id'] for r in rows], ['C2'])
        with self.assertRaises(ValueError): self.build(cid='C2 Name')

    def test_missing_and_unfinished_are_not_zero(self):
        with self.assertRaisesRegex(ValueError, 'No finalized'): self.build()
        self.f.ai_result(complete=False)
        with self.assertRaisesRegex(ValueError, 'No finalized'): self.build()

    def test_existing_precedence_and_subjective_results_preserved(self):
        self.f.ai_result(); self.f.manual_result()
        repo = self.f.service.assessments.tests.repository
        test = repo.get_by_id(self.tid); test['test_type'] = 'subjective'; repo.save(test)
        report = self.build()
        self.assertEqual(report['test_type'], 'subjective')
        self.assertEqual(report['candidates'], self.f.service.list_results(assessment_id=self.aid, test_id=self.tid))
        row = report['candidates'][0]
        self.assertEqual((row['evaluation_type'], row['total_marks'], row['max_marks'], row['percentage']), ('manual', 3, 6, 50))
        self.assertEqual(row['questions'][0]['co'], 'CO1')

    def test_objective_checkpoint_is_reported_without_regrading(self):
        run = self.f.ai_result()
        # These are already-finalized checkpoints; the report must retain their objective fields.
        for pair in run['questions']:
            pair['result']['test_type'] = 'objective'
            pair['result']['correct_option'] = 'B'
        self.f.runs.repository.save(run)
        repo = self.f.service.assessments.tests.repository
        test = repo.get_by_id(self.tid); test['test_type'] = 'objective'; repo.save(test)
        report = self.build()
        self.assertEqual(report['test_type'], 'objective')
        self.assertEqual(report['candidates'][0]['questions'][0]['correct_option'], 'B')
        self.assertEqual(report['candidates'][0]['total_marks'], 1)

    def test_pdf_and_no_mutation(self):
        self.f.manual_result()
        before = {p.name:p.read_bytes() for p in self.f.root.iterdir() if p.is_file()}
        report = self.build(); snapshot = deepcopy(report)
        pdf = render_report_pdf(report)
        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertIn(b'%%EOF', pdf)
        self.assertEqual(report, snapshot)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.f.root.iterdir() if p.is_file()})
        name = self.service.filename(dict(report, assessment_name='CON: bad / name?', test_name='a<b>'))
        self.assertFalse(any(c in name for c in '<>:/\\|?*'))
        self.assertTrue(name.endswith('.pdf'))

    def test_authorization_and_single_result_scan(self):
        with self.assertRaisesRegex(ValueError, 'authorized'):
            self.service.build(self.aid, self.tid, facilitator_id='other')
        self.f.manual_result()
        with patch.object(self.f.service, 'list_results', wraps=self.f.service.list_results) as calls:
            self.build()
        self.assertEqual(calls.call_count, 1)


with patch("dotenv.load_dotenv"):
    import reflex as rx
    import ai_hybrid_evaluator.state.facilitator_state as module


class ReportStateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from ai_hybrid_evaluator.state.auth_state import AuthState
        self.module = module
        self.fixture = fixtures.EvaluationResultTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.manual_result()
        root = rx.State(_reflex_internal_init=True)
        self.auth = root.get_substate(tuple(AuthState.get_full_name().split('.')))
        self.auth.is_authenticated = True
        self.fac = root.get_substate(tuple(module.FacilitatorState.get_full_name().split('.')))
        self.fac.selected_assessment_id = self.fixture.key[1]
        self.fac.selected_test_name = 'Formative 1'
        self.service = ReportService(self.fixture.service)
        change = patch.object(module, 'ReportService', return_value=self.service)
        change.start(); self.addCleanup(change.stop)

    async def test_real_pdf_event_and_single_test_selection(self):
        await self.fac.open_download_pdf_modal()
        self.fac.toggle_download_pdf_test('Formative 2')
        self.assertEqual(self.fac.download_pdf_selected_tests, ['Formative 2'])
        self.fac.toggle_download_pdf_test('Formative 1')
        self.fac.set_download_pdf_report_type('individual')
        self.assertEqual(self.fac.download_pdf_candidate, 'C1 Name (C1)')
        event = await self.fac.download_pdf_modal_submit()
        self.assertFalse(self.fac.show_download_pdf_modal)
        self.assertIn('application/pdf', str(event))

    async def test_stale_scope_rejected_before_download(self):
        await self.fac.open_download_pdf_modal()
        self.fac.selected_assessment_id = self.fixture.b['assessment_id']
        with patch.object(self.service, 'download') as download:
            event = await self.fac.download_pdf_modal_submit()
            download.assert_not_called()
        self.assertIn('Assessment selection changed', str(event))

    async def test_missing_result_keeps_dialog_open(self):
        await self.fac.open_download_pdf_modal()
        self.fac.toggle_download_pdf_test('Formative 2')
        event = await self.fac.download_pdf_modal_submit()
        self.assertTrue(self.fac.show_download_pdf_modal)
        self.assertIn('No finalized', str(event))

    async def test_modal_component_constructs(self):
        from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import _results_download_pdf_modal
        self.assertIsNotNone(_results_download_pdf_modal())


if __name__ == '__main__':
    unittest.main()
