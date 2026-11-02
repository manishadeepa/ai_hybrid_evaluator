import pytest
from test_ai_evaluation_runs import records,result
import test_ai_evaluation_runs as lifecycle

@pytest.fixture
def run_case():
    case=lifecycle.RunTests();case.setUp()
    yield case
    case.doCleanups()

def completed(case):
    run=case.service.start(case.create()['run_id'])
    while True:
        chunk=case.service._next_chunk(run['run_id'],run['execution_token'],10)
        if not chunk: break
        for question in chunk:
            case.service.checkpoint(run['run_id'],run['execution_token'],question['pair_id'],result())
    done=case.service.finish(run['run_id'],run['execution_token'])
    assert done['status']=='completed'
    return done

@pytest.mark.parametrize('action',['restart','start','execute','new-single','new-batch','prepare-single','prepare-batch'])
def test_completed_cannot_be_evaluated_again(run_case,action):
    c=run_case;run=completed(c);before=c.repo.file_path.read_bytes()
    with pytest.raises(ValueError,match='^EVALUATION ALREADY COMPLETED$'):
        if action=='prepare-single':
            c.service.prepare_single('Assessment','Test','C1','Candidate',None,None,**c.ids)
        elif action=='prepare-batch':
            c.service.prepare_batch('Assessment','Test',records(),{'C1':'Candidate'},None,**c.ids)
        elif action.startswith('new'):
            c.service.create_run('Assessment','Test',records(),candidate_scope='all' if action=='new-batch' else 'single',labels={'C1':'Candidate'},**c.ids)
        else:getattr(c.service,action)(run['run_id'])
    assert c.repo.file_path.read_bytes()==before

def test_unevaluated_candidate_still_allowed(run_case):
    c=run_case;completed(c)
    run=c.service.create_run('Assessment','Test',records('C2'),**c.ids)
    assert run['status']=='idle'

def test_legacy_name_scope_cannot_bypass_completion(run_case):
    c=run_case;run=completed(c)
    run['assessment_id']='';run['test_id']=''
    from backend.repositories.json_repository import JSONRepository
    JSONRepository(c.repo.file_path).save_all([run])
    with pytest.raises(ValueError,match='EVALUATION ALREADY COMPLETED'):c.create()
