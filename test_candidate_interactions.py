"""Real Reflex candidate events with isolated canonical response storage."""
import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.repositories.candidate_repository import CandidateRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService
from backend.services.response_lifecycle_service import ResponseLifecycleService
from backend.services.question_paper_service import QuestionPaperService
from test_automatic_objective import workbook
with patch("dotenv.load_dotenv"):
    import reflex as rx
    import ai_hybrid_evaluator.state.candidate_state as module
    from ai_hybrid_evaluator.state.auth_state import AuthState

async def finish(event):
    return [item async for item in event]

class CandidateInteractionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name); cwd=Path.cwd(); os.chdir(self.path); self.addCleanup(os.chdir,cwd)
        self.candidates=CandidateManagementService(CandidateRepository(self.path/'candidates.json'))
        self.candidates.create_candidate(dict(candidate_id='TEST-C',name='Candidate',email='test@example.com'))
        self.service=self.candidates.assessments
        self.a=self.service.create_assessment(dict(name='Objective',tests=['Formative 1'],assigned_candidates=['TEST-C']))
        self.aid=self.a['assessment_id']; self.tid=self.a['test_ids']['Formative 1']
        QuestionPaperService(self.service.tests).import_upload(self.aid,self.tid,'paper.xlsx',workbook())
        self.lifecycle=ResponseLifecycleService(CandidateAssignmentService(self.candidates))
        self.root=rx.State(_reflex_internal_init=True)
        self.state=self.root.get_substate(tuple(module.CandidateState.get_full_name().split('.')))
        auth=self.root.get_substate(tuple(AuthState.get_full_name().split('.')))
        auth.candidate_emp_id='TEST-C'; auth.is_candidate_authenticated=True
        for name,value in [('AssessmentService',self.service),('ResponseLifecycleService',self.lifecycle)]:
            p=patch.object(module,name,return_value=value);p.start();self.addCleanup(p.stop)
        p=patch.dict(module.PERSISTED_CANDIDATE_TEST_DATA,{},clear=True);p.start();self.addCleanup(p.stop)

    async def start(self):
        return await self.state.start_test('Objective','Formative 1')

    async def test_precomputed_empty_questions_are_invalidated_on_start(self):
        self.assertEqual(self.state.current_question,{})
        self.assertEqual(self.state.current_question_type,'Subjective')
        self.assertEqual(self.state.total_questions,0)
        events=await self.start()
        self.assertEqual(self.state.total_questions,3)
        self.assertEqual(self.state.current_question_type,'Objective')
        self.assertEqual(self.state.current_option_b,'Beta')
        self.assertEqual(self.lifecycle.get_status('TEST-C',self.aid,self.tid),'In Progress')
        self.assertFalse(self.state.is_fullscreen)
        self.assertNotIn('run_timer',str(events))

    async def test_visual_answer_yields_before_any_persistence(self):
        await self.start()
        displayed_qid = self.state.current_question_number
        with patch.object(self.lifecycle,'save_answer',wraps=self.lifecycle.save_answer) as save:
            event=self.state.select_mcq_option('B')
            await anext(event)
            self.assertEqual(self.state.current_mcq_answer,'B')
            self.assertEqual(self.state.auto_save_status,'Saving...')
            save.assert_not_called()
            await finish(event)
            save.assert_called_once()
        self.assertEqual(
            self.lifecycle.get_answers('TEST-C',self.aid,self.tid),
            {str(displayed_qid): 'B'}
        )
        self.assertEqual(self.state.auto_save_status,'Auto-saved')

    async def test_same_option_skips_duplicate_write(self):
        await self.start(); await finish(self.state.select_mcq_option('A'))
        with patch.object(self.lifecycle,'save_answer') as save:
            await finish(self.state.select_mcq_option('A')); save.assert_not_called()

    async def test_navigation_answers_clear_review_and_reload(self):
        await self.start()
        displayed_qid = self.state.current_question_number
        await finish(self.state.select_mcq_option('B'))
        with patch.object(self.lifecycle,'save_answer') as save:
            self.state.save_and_next_question(); self.state.prev_question(); save.assert_not_called()
        self.assertEqual(self.state.current_mcq_answer,'B')
        await finish(self.state.toggle_mark_for_review())
        await finish(self.state.clear_mcq_answer())
        fresh=ResponseLifecycleService(CandidateAssignmentService(self.candidates))
        rec=fresh.get_response('TEST-C',self.aid,self.tid)
        self.assertEqual(rec['answers'][str(displayed_qid)], '')
        self.assertEqual(rec['marked_for_review'], [displayed_qid])
        await self.start()
        self.assertEqual(self.state.current_mcq_answer,'')
        self.assertTrue(self.state.is_current_marked)

    async def test_save_failure_is_visible_and_navigation_does_not_claim_success(self):
        await self.start()
        with patch.object(self.lifecycle,'save_answer',side_effect=OSError('disk unavailable')):
            await finish(self.state.select_mcq_option('B'))
        self.assertEqual(self.state.auto_save_status,'Save failed')
        self.state.save_and_next_question()
        self.assertEqual(self.state.auto_save_status,'Save failed')

    async def test_submission_persisted_and_cannot_restart(self):
        await self.start()
        displayed_qid = self.state.current_question_number
        await finish(self.state.select_mcq_option('B'))
        await finish(self.state.confirm_submit_test())
        self.assertTrue(self.state.is_test_submitted)
        record=self.lifecycle.get_response('TEST-C',self.aid,self.tid)
        self.assertEqual(record['status'],'Submitted')
        self.assertEqual(record['answers'][str(displayed_qid)],'B')
        with self.assertRaises(ValueError): self.lifecycle.start_test('TEST-C',self.aid,self.tid)
        await finish(self.state.select_mcq_option('A'))
        self.assertEqual(self.state.current_mcq_answer,'B')

    async def test_fullscreen_initial_exit_and_duplicate_exit(self):
        await self.start()
        await finish(self.state.sync_fullscreen(False)); self.assertEqual(self.state.violation_count,0)
        await finish(self.state.sync_fullscreen(True)); self.assertTrue(self.state.is_fullscreen)
        self.state.exit_fullscreen(); self.assertEqual(self.state.violation_count,0)
        await finish(self.state.handle_fullscreen_exited()); self.assertFalse(self.state.is_fullscreen)
        self.assertEqual(self.state.violation_count,1)
        await finish(self.state.handle_fullscreen_exited()); self.assertEqual(self.state.violation_count,1)
        self.state.is_test_submitted=True; self.state.handle_fullscreen_entered()
        await finish(self.state.handle_fullscreen_exited()); self.assertFalse(self.state.is_fullscreen)

    async def test_late_subjective_relay_keeps_original_question_identity(self):
        import json
        await self.start()
        self.state.questions=[dict(q, question_type="Subjective") for q in self.state.questions]
        self.state.next_question()
        displayed_after_next = self.state.current_question_number
        await finish(self.state.set_answer_payload(json.dumps({"question_id":1,"html":"Original answer"})))
        self.assertEqual(self.lifecycle.get_answers('TEST-C',self.aid,self.tid),{'1':'Original answer'})
        self.assertEqual(self.state.current_question_number, displayed_after_next)

    async def test_disk_work_is_zero_before_visual_update_and_zero_on_navigation(self):
        from backend.repositories.json_repository import JSONRepository
        await self.start()
        reads=[]; writes=[]
        read=JSONRepository._read_data; write=JSONRepository._write_data
        def counted_read(repo):
            reads.append(repo.file_path.name); return read(repo)
        def counted_write(repo,rows):
            writes.append(repo.file_path.name); return write(repo,rows)
        with patch.object(JSONRepository,'_read_data',counted_read), patch.object(JSONRepository,'_write_data',counted_write):
            event=self.state.select_mcq_option('B'); await anext(event)
            self.assertEqual((reads,writes),([],[]))
            await finish(event)
            print("Answer durability phase: %d JSON reads, %d JSON writes; visual phase: 0 reads/writes" % (len(reads),len(writes)))
            reads.clear(); writes.clear()
            self.state.next_question(); self.state.prev_question()
            self.assertEqual((reads,writes),([],[]))

    async def test_component_builds_with_native_radio(self):
        from ai_hybrid_evaluator.pages.candidate.candidate_test import candidate_test_page
        self.assertIsNotNone(candidate_test_page())

class AtomicWriterTests(unittest.TestCase):
    def test_transient_windows_lock_retries_without_truncation(self):
        from backend.repositories.json_repository import JSONRepository
        with tempfile.TemporaryDirectory() as folder:
            repo=JSONRepository(Path(folder)/'probe.json'); repo.save_all([{'old':True}])
            error=PermissionError('locked'); error.winerror=32
            real_replace=os.replace; calls=[]
            def replace(source,target):
                calls.append(1)
                if len(calls)<3:
                    self.assertEqual(repo.get_all(),[{'old':True}]); raise error
                return real_replace(source,target)
            with patch('backend.repositories.json_repository.os.replace',side_effect=replace), patch('backend.repositories.json_repository.time.sleep'):
                repo.save_all([{'new':True}])
            self.assertEqual(len(calls),3); self.assertEqual(repo.get_all(),[{'new':True}])

    def test_persistent_windows_lock_is_reported_and_preserves_old_file(self):
        from backend.repositories.json_repository import JSONRepository
        with tempfile.TemporaryDirectory() as folder:
            repo=JSONRepository(Path(folder)/'probe.json'); repo.save_all([{'old':True}])
            error=PermissionError('locked'); error.winerror=5
            with patch('backend.repositories.json_repository.os.replace',side_effect=error) as replace, patch('backend.repositories.json_repository.time.sleep'):
                with self.assertRaises(PermissionError): repo.save_all([{'new':True}])
            self.assertEqual(replace.call_count,4); self.assertEqual(repo.get_all(),[{'old':True}])
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])

class BrowserBridgeTests(unittest.TestCase):
    def test_real_fullscreen_script_initial_sync_dedup_and_unmounted_guards(self):
        import ast
        import json
        import shutil
        import subprocess
        node=shutil.which("node")
        if not node: self.skipTest("Node is required for the browser bridge test")
        path=Path(__file__).parent/'ai_hybrid_evaluator/pages/candidate/candidate_test.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        script=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'function checkFS()' in n.value)
        harness = r"""
const assert = require('node:assert/strict');
let entered=0, exited=0, tab=0, mounted=true;
const listeners={};
global.window={addEventListener(){},removeEventListener(){}};
global.document={fullscreenElement:null,hidden:false,
 addEventListener(n,f){listeners[n]=f},removeEventListener(){},
 getElementById(id){
  if(!mounted)return null;
  if(id==='fs-enter-btn')return {click(){entered++}};
  if(id==='fs-exit-btn')return {click(){exited++}};
  if(id==='tab-switch-btn')return {disabled:false,click(){tab++}};
  return null;
 }};
""" + script + r"""
assert.equal(exited,1); assert.equal(entered,0);
document.fullscreenElement={}; listeners.fullscreenchange(); listeners.webkitfullscreenchange();
assert.equal(entered,1);
document.fullscreenElement=null; listeners.fullscreenchange(); listeners.webkitfullscreenchange();
assert.equal(exited,2);
mounted=false; window.__candidate_blur_handler(); window.__candidate_beforeunload({});
assert.equal(tab,0);
console.log('Fullscreen browser bridge: initial state, transitions, duplicate suppression and unmounted guards OK');
"""
        result=subprocess.run([node,'-e',harness],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        print(result.stdout.strip())

if __name__=='__main__': unittest.main()
