import ast,asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

def handler(name,service):
    staged=Path(__file__).with_name('facilitator_feedback_retry.fixed.py')
    path=staged if staged.exists() else Path(__file__).parent/'ai_hybrid_evaluator/state/facilitator_state.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FacilitatorState')
    node=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
    node.decorator_list=[]
    ns={'AuthState':object(),'FeedbackService':lambda:service,'rx':SimpleNamespace(toast=SimpleNamespace(success=lambda text:('success',text),error=lambda text:('error',text)))}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
    return ns[name]

def state():
    async def get_state(_):return SimpleNamespace(facilitator_emp_id='F001')
    return SimpleNamespace(get_state=get_state, selected_assessment_id='A', selected_assessment_name='QFD 3',show_facilitator_feedback_modal=True,close_assessment_feedback_additional='new text',close_assessment_feedback_answers={'q1':'new answer'},close_assessment_feedback_additional_error='',close_assessment_feedback_questions=[{'id':'q1','rating':4}])

@pytest.mark.parametrize('name',['confirm_close_assessment','submit_facilitator_feedback_modal'])
def test_already_saved_retry_closes_without_overwrite(name):
    service=SimpleNamespace(pending_form=Mock(return_value=None),resolve_form=Mock(return_value={'feedback_form_id':'F'}),close_assessment=Mock(),submit=Mock())
    s=state();result=asyncio.run(handler(name,service)(s))
    assert result[0]=='success'
    assert not s.show_facilitator_feedback_modal
    assert s.close_assessment_feedback_answers=={}
    service.close_assessment.assert_called_once_with('F001','A')
    service.submit.assert_not_called()

def test_missing_configuration_does_not_close():
    service=SimpleNamespace(pending_form=Mock(return_value=None),resolve_form=Mock(return_value=None),close_assessment=Mock())
    s=state();result=asyncio.run(handler('submit_facilitator_feedback_modal',service)(s))
    assert result[0]=='error' and 'contact Admin' in result[1]
    service.close_assessment.assert_not_called()

def test_failed_close_preserves_form_and_answers():
    service=SimpleNamespace(pending_form=Mock(return_value=None),resolve_form=Mock(return_value={'feedback_form_id':'F'}),close_assessment=Mock(side_effect=ValueError('Close failed')),submit=Mock())
    s=state();result=asyncio.run(handler('submit_facilitator_feedback_modal',service)(s))
    assert result==('error','Close failed')
    assert s.show_facilitator_feedback_modal
    assert s.close_assessment_feedback_answers=={'q1':'new answer'}
    service.submit.assert_not_called()

def test_new_feedback_still_saves_ratings_and_comments():
    service=SimpleNamespace(pending_form=Mock(return_value={'feedback_form_id':'F'}),close_assessment=Mock(),submit=Mock())
    s=state();result=asyncio.run(handler('submit_facilitator_feedback_modal',service)(s))
    assert result[0]=='success'
    assert service.submit.call_args.kwargs=={'ratings':{'q1':4},'additional_feedback':'new text'}
    assert not s.show_facilitator_feedback_modal
