"""Candidate interaction regressions with isolated stores and actual browser bridge JS."""
import asyncio
import ast
import json
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from unittest.mock import patch
import test_candidate_interactions as fixtures


class CandidatePerformanceTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.CandidateInteractionTests.setUp
    start = fixtures.CandidateInteractionTests.start

    async def test_shuffled_navigation_uses_positions_and_preserves_ids_on_reload(self):
        with patch('backend.services.response_lifecycle_service.random.shuffle', side_effect=lambda q:q.reverse()):
            await self.start()
        self.assertEqual([q['id'] for q in self.state.questions], [3,2,1])
        self.assertEqual([q['number'] for q in self.state.nav_questions], ['1','2','3'])
        for position, identity in [(1,3),(2,2),(3,1)]:
            self.state.jump_to_question(position)
            self.assertEqual(self.state.current_question_number,identity)
            self.assertEqual(self.state.current_question_display_number,position)
            self.assertEqual(self.state.nav_questions[position-1]['position'],position)
        self.state.jump_to_question(1)
        await fixtures.finish(self.state.select_mcq_option('B'))
        await fixtures.finish(self.state.toggle_mark_for_review())
        self.state.save_and_next_question();self.assertEqual(self.state.current_question_index,1)
        self.state.next_question();self.assertEqual(self.state.current_question_index,2)
        self.state.prev_question();self.assertEqual(self.state.current_question_index,1)
        await fixtures.finish(self.state.select_mcq_option('A'))
        await fixtures.finish(self.state.clear_mcq_answer())
        self.assertEqual(self.lifecycle.get_answers('TEST-C',self.aid,self.tid),{'3':'B','2':''})
        await self.start()
        self.assertEqual([q['id'] for q in self.state.questions],[3,2,1])
        self.assertEqual(self.state.current_mcq_answer,'B')
        self.assertEqual(self.state.marked_for_review,[3])

    async def test_fourteen_navigation_labels(self):
        await self.start()
        prototype=self.state.questions[0]
        ids=[14,6,13,2,8,7,12,11,4,5,9,3,1,10]
        self.state.questions=[dict(prototype,id=i) for i in ids]
        self.assertEqual([q['number'] for q in self.state.nav_questions],list(map(str,range(1,15))))
        for position,identity in enumerate(ids,1):
            self.state.jump_to_question(position)
            self.assertEqual(self.state.current_question_number,identity)
            self.assertEqual(self.state.current_question_display_number,position)

    async def test_warning_is_visible_before_slow_io_and_io_does_not_block_loop(self):
        await self.start()
        entered=threading.Event();release=threading.Event()
        original=self.lifecycle.update_violation_count
        def slow(*args):
            entered.set()
            if not release.wait(3):raise RuntimeError('test timed out')
            return original(*args)
        with patch.object(self.lifecycle,'update_violation_count',side_effect=slow):
            event=self.state.trigger_proctoring_warning()
            await anext(event)
            self.assertTrue(self.state.show_violation_modal)
            self.assertFalse(entered.is_set())
            task=asyncio.create_task(fixtures.finish(event))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait,1))
                # The event loop remains available while persistence is stalled.
                await asyncio.wait_for(asyncio.sleep(.01),.2)
            finally:
                release.set();await task
        self.assertEqual(self.lifecycle.get_response('TEST-C',self.aid,self.tid)['violation_count'],1)

    async def test_three_violations_still_durably_disqualify(self):
        await self.start()
        for _ in range(3):
            self.state.dismiss_violation_modal()
            await fixtures.finish(self.state.trigger_proctoring_warning())
        self.assertTrue(self.state.is_test_submitted)
        self.assertEqual(self.state.violation_count,3)
        self.assertEqual(self.lifecycle.get_status('TEST-C',self.aid,self.tid),'Disqualified')
        await fixtures.finish(self.state.trigger_proctoring_warning())
        self.assertEqual(self.state.violation_count,3)

    async def test_minimize_signals_count_once_until_acknowledged(self):
        await self.start()
        self.state.handle_fullscreen_entered()
        await fixtures.finish(self.state.trigger_proctoring_warning())
        await fixtures.finish(self.state.handle_fullscreen_exited())
        await fixtures.finish(self.state.trigger_proctoring_warning())
        self.assertEqual(self.state.violation_count, 1)
        self.assertFalse(self.state.is_disqualified)
        self.assertFalse(self.state.is_fullscreen)
        self.assertEqual(self.lifecycle.get_response('TEST-C', self.aid, self.tid)['violation_count'], 1)

    async def test_navigation_updates_before_disk_and_saves_outgoing_identity(self):
        await self.start()
        self.state.questions = [dict(q, question_type='Subjective') for q in self.state.questions]
        qid = self.state.current_question_number
        with patch.object(self.lifecycle, 'save_answer', wraps=self.lifecycle.save_answer) as save:
            event = self.state.next_with_answer(json.dumps({'question_id':qid, 'html':'latest answer'}))
            await anext(event)
            self.assertEqual(self.state.current_question_index, 1)
            save.assert_not_called()
            await fixtures.finish(event)
            save.assert_called_once()
        self.assertEqual(self.lifecycle.get_answers('TEST-C', self.aid, self.tid)[str(qid)], 'latest answer')
        await fixtures.finish(self.state.previous_with_answer(''))
        self.assertEqual(self.state.current_question_number, qid)
        self.assertEqual(self.state.answers[str(qid)], 'latest answer')

    async def test_clear_captures_id_before_yield(self):
        await self.start()
        qid=self.state.current_question_number
        await fixtures.finish(self.state.select_mcq_option('B'))
        clear=self.state.clear_mcq_answer();await anext(clear)
        self.state.next_question()
        await fixtures.finish(clear)
        self.assertEqual(self.lifecycle.get_answers('TEST-C',self.aid,self.tid),{str(qid):''})

    async def test_submit_captures_latest_editor_and_persists_before_success(self):
        await self.start()
        qid=self.state.current_question_number
        self.state.questions=[dict(q,question_type='Subjective') for q in self.state.questions]
        event=self.state.confirm_submit_test(json.dumps(dict(question_id=qid,html='Latest typed answer')))
        await anext(event)
        self.assertTrue(self.state.is_submitting)
        self.assertFalse(self.state.is_test_submitted)
        await fixtures.finish(event)
        self.assertTrue(self.state.is_test_submitted)
        record=self.lifecycle.get_response('TEST-C',self.aid,self.tid)
        self.assertEqual(record['answers'][str(qid)],'Latest typed answer')

    async def test_failed_submit_preserves_editable_state(self):
        await self.start()
        with patch.object(self.lifecycle,'submit',side_effect=OSError('disk unavailable')):
            await fixtures.finish(self.state.confirm_submit_test())
        self.assertFalse(self.state.is_submitting)
        self.assertFalse(self.state.is_test_submitted)

    async def test_timer_counts_down_and_expires_once(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        class TimerState(SimpleNamespace):
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
        timer=TimerState(timer_session_id=1,is_test_submitted=False,is_time_expired=False,
            total_time_seconds=3,time_display='',handle_time_expired=AsyncMock())
        with patch.object(fixtures.module.asyncio, 'sleep', new=AsyncMock()) as sleep:
            await fixtures.module.CandidateState.run_timer.fn(timer)
        self.assertEqual(timer.total_time_seconds,0)
        self.assertEqual(timer.time_display,'00:00:00')
        timer.handle_time_expired.assert_awaited_once()
        self.assertEqual(sleep.await_count,4)



class CandidateBrowserPerformanceTests(unittest.TestCase):
    @staticmethod
    def script():
        path=Path(__file__).parent/'ai_hybrid_evaluator/pages/candidate/candidate_test.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '__candidate_fs_handler' in n.value)

    def node(self, code):
        node=shutil.which('node')
        if not node:self.skipTest('Node required for browser event checks')
        result=subprocess.run(
            [node],
            input=code.encode('utf-8'),
            capture_output=True,
        )
        stderr = result.stderr.decode('utf-8', errors='replace')
        self.assertEqual(result.returncode,0,stderr)

    def test_tab_blur_visibility_deduplicated_until_real_return(self):
        self.node(r"""
const assert=require('node:assert/strict');let tab=0,focused=true,mounted=true;const listeners={};let timers=[];
global.setTimeout=(f,ms)=>{timers.push(f);return timers.length};
global.clearTimeout=()=>{};
global.window={addEventListener(){},removeEventListener(){},focus(){}};
global.document={fullscreenElement:{},hidden:false,hasFocus(){return focused},
 addEventListener(n,f){listeners[n]=f},removeEventListener(){},
 getElementById(id){return mounted && id==='tab-switch-btn'?{disabled:false,click(){tab++}}:null}};
"""+self.script()+r"""
focused=false;window.__candidate_blur_handler();document.hidden=true;listeners.visibilitychange();
window.__candidate_blur_handler();assert.equal(tab,1);
document.hidden=false;listeners.visibilitychange();window.__candidate_blur_handler();assert.equal(tab,1);
focused=true;window.__candidate_return_handler();
timers.splice(0).forEach(f=>f());
focused=false;window.__candidate_blur_handler();assert.equal(tab,2);
mounted=false;window.__candidate_blur_handler();assert.equal(tab,2);
""")

    def test_minimize_fullscreen_blur_hidden_and_script_remount_are_one_episode(self):
        self.node(r"""
const assert=require('node:assert/strict');let alerts=0,focused=true;let timers=[];
global.setTimeout=(f,ms)=>{timers.push(f);return timers.length};
global.clearTimeout=()=>{};
global.window={addEventListener(){},removeEventListener(){},focus(){}};
global.document={fullscreenElement:{},hidden:false,hasFocus(){return focused},addEventListener(){},removeEventListener(){},getElementById(id){return ['fs-exit-btn','tab-switch-btn'].includes(id)?{disabled:false,click(){alerts++}}:null}};
"""+self.script()+r"""
focused=false;window.__candidate_blur_handler();document.fullscreenElement=null;
window.__candidate_fs_handler();document.hidden=true;window.__candidate_vis_handler();
assert.equal(alerts,1);
"""+self.script()+r"""
window.__candidate_blur_handler();window.__candidate_vis_handler();assert.equal(alerts,1);
document.hidden=false;focused=true;document.fullscreenElement={};window.__candidate_fs_handler();

// Complete the delayed return/rearm before starting a new away episode.
window.__candidate_return_handler();
timers.splice(0).forEach(f=>f());

focused=false;window.__candidate_blur_handler();assert.equal(alerts,2);
""")

    def test_printscreen_uses_same_episode_and_deduplicates_with_blur(self):
        self.node(r"""
const assert=require('node:assert/strict');
let alerts=0,focused=true,mounted=true;
let timers=[];
const listeners={};

global.setTimeout=(f,ms)=>{
    timers.push(f);
    return timers.length;
};
global.clearTimeout=()=>{};

global.window={
    addEventListener(n,f){listeners['window:'+n]=f},
    removeEventListener(){},
    focus(){}
};

global.document={
    fullscreenElement:{},
    hidden:false,
    hasFocus(){return focused},
    addEventListener(n,f){listeners[n]=f},
    removeEventListener(){},
    getElementById(id){
        if(!mounted)return null;
        if(id==='tab-switch-btn'){
            return {
                disabled:false,
                click(){alerts++}
            };
        }
        return null;
    }
};
"""+self.script()+r"""

// PrintScreen creates one violation.
window.__candidate_screenshot_handler({key:'PrintScreen'});
assert.equal(alerts,1);

// Blur/visibility from the same physical episode must NOT add warnings.
focused=false;
window.__candidate_blur_handler();
document.hidden=true;
window.__candidate_vis_handler();
assert.equal(alerts,1);

// Ordinary keys must not count.
window.__candidate_screenshot_handler({key:'A'});
assert.equal(alerts,1);

// Candidate genuinely returns.
document.hidden=false;
focused=true;
window.__candidate_return_handler();
timers.splice(0).forEach(f=>f());

// A NEW PrintScreen incident may now create exactly one new warning.
window.__candidate_screenshot_handler({key:'PrintScreen'});
assert.equal(alerts,2);

// Same episode still remains deduplicated.
focused=false;
window.__candidate_blur_handler();
assert.equal(alerts,2);

// Unmounted relay must be safe.
mounted=false;
window.__candidate_screenshot_handler({key:'PrintScreen'});
assert.equal(alerts,2);
""")

    def test_editor_coalesces_burst_and_keeps_original_question_on_flush(self):
        script=self.script();begin=script.index('                            var relayTimer');end=script.index('// ── RTE restore',begin)
        self.node(r"""
const assert=require('node:assert/strict');let timers=[],messages=[],stored=[];
global.setTimeout=(f,ms)=>{timers.push(f);return timers.length};global.clearTimeout=()=>{};
global.Event=class{constructor(type){this.type=type}};
global.window={__updateWordCount(){},__rteSaveToStorage(x){stored.push(x)},HTMLTextAreaElement:function(){}};
Object.defineProperty(window.HTMLTextAreaElement.prototype,'value',{set(v){this.valueText=v}});
const relay={dataset:{questionId:'14',candidateId:'C',assessment:'A',testName:'T'},dispatchEvent(){messages.push(JSON.parse(this.valueText))}};
const input={};const ed={innerHTML:'',addEventListener(n,f){input[n]=f}};
global.document={getElementById(id){return id==='rte-relay'?relay:id==='rte-editor'?ed:null}};
"""+script[begin:end]+r"""
window.bindRteInput(ed);
for(let i=1;i<=100;i++){ed.innerHTML='answer '+i;input.input()}
assert.equal(stored.length,100);assert.equal(messages.length,0);assert.equal(timers.length,100);
relay.dataset.questionId='6';timers[timers.length-1]();assert.deepEqual(messages,[{question_id:'14',html:'answer 100'}]);
ed.innerHTML='next';input.input();window.__rteSaveCurrentAnswer();assert.equal(messages.length,2);
assert.deepEqual(messages[1],{question_id:'6',html:'next'});
""")

    def test_radio_and_highlight_use_same_controlled_state(self):
        from ai_hybrid_evaluator.pages.candidate.candidate_test import _mcq_option_card
        from test_candidate_interactions import module
        rendered=str(_mcq_option_card('A',module.CandidateState.current_option_a))
        self.assertIn('checked',rendered)
        self.assertNotIn('defaultChecked',rendered)

if __name__=='__main__':unittest.main()
