import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import pytest
from backend.services.evaluation_status_service import summarize_evaluation
from ai_hybrid_evaluator.state.facilitator_state import _evaluation_candidate_id
import test_evaluation_result_management as result_tests

def result(cid="C1", **values):
    return {"assessment_id":"A", "test_id":"T", "candidate_id":cid, "evaluation_status":"completed", **values}

@pytest.mark.parametrize("rows,status,count",[([],"Pending",0),([result()],"In Progress",1),([result(),result("C2")],"Completed",2)])
def test_test_status_comes_from_saved_final_results(rows,status,count):
    summary=summarize_evaluation("A","T",["C1","C2","C1"],rows)
    assert summary=={"status":status,"completed":count,"total":2}

def test_zero_scores_and_duplicate_rows_do_not_distort_completion():
    assert summarize_evaluation("A","T",["C1"],[result(total_marks=0),result(total_marks=0)])["status"]=="Completed"

def test_selected_candidate_is_independent_of_other_pending_candidates():
    summary=summarize_evaluation("A","T",["C1","C2"],[result()],candidate_id="C1")
    assert summary=={"status":"Completed","completed":1,"total":1}

@pytest.mark.parametrize("row",[result(assessment_id="OTHER"),result(test_id="OTHER"),result("OTHER"),result(evaluation_status="running",score="100 / 100"),result(evaluation_status="failed")])
def test_other_scopes_or_unfinished_results_do_not_complete_test(row):
    assert summarize_evaluation("A","T",["C1"],[row])["status"]=="Pending"

def test_active_run_is_in_progress_not_completed():
    assert summarize_evaluation("A","T",["C1"],[],active=True)["status"]=="In Progress"
    assert summarize_evaluation("A","T",[],[],active=True)["status"]=="Pending"

class AwaitableValue:
    def __init__(self,value):self.value=value
    def __await__(self):
        async def resolve():return self.value
        return resolve().__await__()

def state_summary(**changes):
    source=Path(__file__).parent/'ai_hybrid_evaluator/state/facilitator_state.py'
    cls=next(n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='FacilitatorState')
    node=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='evaluation_status_summary')
    node.decorator_list=[]
    namespace={'_evaluation_candidate_id':_evaluation_candidate_id}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    assessment={"assessment_id":"A", "name":"Assessment", "test_ids":{"Formative 1":"T"}, "assigned_candidates":["C1","C2"]}
    state=SimpleNamespace(selected_assessment_id="A",selected_assessment_name="Assessment",selected_test_name="Formative 1",selected_evaluation_test="Formative 1",selected_evaluation_candidate="",my_assessments=AwaitableValue([assessment]),_workspace_snapshot={"scope":["A","Assessment","Formative 1",""],"errors":[]},assessment_evaluation_results={"arbitrary display key":result(),"another key":result("C2")},_last_ai_revision=(),ai_run_status="idle")
    for key,value in changes.items():setattr(state,key,value)
    return asyncio.run(namespace['evaluation_status_summary'](state))

def test_placeholder_selection_uses_overall_test_and_ignores_display_keys():
    assert state_summary()["status"]=="Completed"

def test_renamed_candidate_selection_uses_id():
    summary=state_summary(selected_evaluation_candidate="Renamed Candidate (C1)",assessment_evaluation_results={"old label":result()})
    assert summary["status"]=="Completed" and summary["test_completed_count"]==1

def test_refresh_failure_is_not_reported_as_pending():
    assert state_summary(_workspace_snapshot={"scope":["A","Assessment"],"errors":["Cannot read results"]})["status"]=="Unable to load"
    assert state_summary(_workspace_snapshot={})["status"]=="Loading"

def test_running_other_test_cannot_change_selected_test_status():
    summary=state_summary(assessment_evaluation_results={},ai_run_status="running",_last_ai_revision=("R","time","running","Assessment","Other","", "A", "OTHER"))
    assert summary["status"]=="Pending"

@pytest.mark.parametrize("method",["manual","ai"])
def test_saved_manual_and_ai_results_survive_status_reload(method):
    case=result_tests.EvaluationResultTests();case.setUp()
    try:
        case.manual_result() if method=="manual" else case.ai_result()
        normalized=case.service.list_results()
        assert summarize_evaluation(case.key[1],case.key[2],["C1"],normalized)["status"]=="Completed"
    finally:case.doCleanups()
