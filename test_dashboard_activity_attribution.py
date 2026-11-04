from copy import deepcopy
from types import SimpleNamespace
import pytest
from backend.services.facilitator_dashboard_service import FacilitatorDashboardService
import test_evaluation_result_management as result_tests

class Store:
    def __init__(self, rows): self.rows = rows
    def get_all(self): return deepcopy(self.rows)

@pytest.fixture
def dashboard():
    assessment = {"assessment_id":"A", "name":"Assessment", "assigned_candidates":["C1"],
                  "all_tests":["Formative 1"], "test_ids":{"Formative 1":"T"}}
    test = {"assessment_id":"A", "test_id":"T", "test_name":"Formative 1", "is_locked":False, "created_by":"F001"}
    evaluation = {"assessment_id":"A", "test_id":"T", "assessment_name":"Assessment", "test_name":"Formative 1",
                  "candidate_id":"C1", "evaluation_status":"completed", "evaluated_by_id":"F001"}
    rows = [evaluation]
    results = SimpleNamespace(list_results=lambda:deepcopy(rows), assessments=SimpleNamespace(list_tests=lambda aid:[deepcopy(test)]))
    directory = Store([{"emp_id":"F001","name":"Actual Evaluator","password":"private"}, {"emp_id":"F002","name":"Actual Locker"}])
    submitted = Store([{"candidate_id":"C1","assessment_id":"A","test_id":"T","status":"Submitted"}])
    service = FacilitatorDashboardService(results, submitted, submitted, lambda *args:{}, facilitator_repository=directory)
    def activity():
        overview = service.get_assessments_overview([assessment])[0]
        return service.collaboration_activity(assessment,overview)[0]
    return assessment,test,rows,directory,service,activity

def test_completed_evaluation_does_not_imply_locked(dashboard):
    *_, activity = dashboard
    row = activity()
    assert row["evaluation_status"] == "Completed"
    assert row["evaluated_by"] == "Actual Evaluator"
    assert row["lock_status"] == "Unlocked" and row["locked_by"] == "-"
    assert "private" not in str(row)

def test_locker_is_independent_of_evaluator(dashboard):
    _, test, _, _, _, activity = dashboard
    test.update(is_locked=True, locked_by="F002")
    row = activity()
    assert row["evaluated_by"] == "Actual Evaluator"
    assert row["locked_by"] == "Actual Locker" and row["lock_status"] == "Locked"

def test_locked_test_without_evaluation_uses_real_lock(dashboard):
    _,test,rows,_,_,activity = dashboard
    rows.clear();test.update(is_locked=True, locked_by="F002")
    row=activity()
    assert row["evaluation_status"] == "In Progress"
    assert row["evaluated_by"] == "-" and row["locked_by"] == "Actual Locker"

def test_legacy_missing_actors_are_not_guessed_from_creator(dashboard):
    _,test,rows,_,_,activity = dashboard
    rows[0].pop("evaluated_by_id");test.update(is_locked=True, locked_by="")
    row=activity()
    assert row["evaluated_by"] == row["locked_by"] == "Not recorded"

def test_current_persisted_directory_name_is_used(dashboard):
    _,_,_,directory,_,activity = dashboard
    directory.rows[0]["name"]="Renamed Facilitator"
    assert activity()["evaluated_by"] == "Renamed Facilitator"

def test_deleted_actor_id_is_preserved(dashboard):
    _,test,rows,_,_,activity = dashboard
    rows[0]["evaluated_by_id"]="F009";test.update(is_locked=True,locked_by="F010")
    assert activity()["evaluated_by"] == "F009"
    assert activity()["locked_by"] == "F010"

@pytest.mark.parametrize("field,value", [("assessment_id","OTHER"),("test_id","OTHER")])
def test_same_name_other_identity_does_not_leak_actor(dashboard,field,value):
    _,_,rows,_,_,activity = dashboard
    rows[0][field]=value
    row=activity()
    assert row["evaluated_by"]=="-"
    assert row["evaluation_status"]=="In Progress"

def test_pending_evaluation_has_no_evaluated_by(dashboard):
    _,_,rows,_,_,activity=dashboard
    rows[0]["evaluation_status"]="running"
    assert activity()["evaluated_by"]=="-"

@pytest.fixture
def result_case():
    case=result_tests.EvaluationResultTests();case.setUp()
    yield case
    case.doCleanups()

@pytest.mark.parametrize("method",["manual","ai"])
def test_actor_metadata_is_saved_and_reloaded_from_authenticated_action(result_case,method):
    case=result_case
    saved=case.manual_result() if method=="manual" else case.ai_result()
    assert saved["evaluated_by_id"]=="F001"
    assert saved["evaluated_by"]=="F001"
    if method=="ai":assert case.runs.repository.get(saved["run_id"])["evaluated_by_id"]=="F001"
    else:assert case.manual.get_all()[0]["evaluated_by_id"]=="F001"
    result=case.service.get_result(*case.key)
    assert result["evaluated_by_id"]=="F001"
    assert result["evaluated_by"]=="F001"

def test_canonical_actor_id_wins_over_legacy_label(result_case):
    case=result_case;saved=case.manual_result()
    saved["evaluated_by"]="Misleading label"
    case.manual.save(saved,facilitator_id="F001",role="facilitator")
    assert case.service.get_result(*case.key)["evaluated_by"]=="F001"


def test_unlocked_test_does_not_display_stale_lock_actor(dashboard):
    _,test,_,_,_,activity=dashboard
    test.update(is_locked=False,locked_by="F002")
    assert activity()["locked_by"]=="-"
