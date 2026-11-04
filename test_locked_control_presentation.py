import ast
from pathlib import Path
import reflex as rx
from ai_hybrid_evaluator.components.locked_controls import locked_control, LOCKED_MESSAGE
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState

def walk(component):
    yield component
    for child in component.children:
        if isinstance(child,rx.Component):yield from walk(child)

def test_locked_branch_has_no_original_mutation_events():
    original=rx.button("Replace File",disabled=FacilitatorState.is_selected_test_locked,
                       on_click=FacilitatorState.start_replacing_qp("Formative 1"),background="purple")
    wrapped=locked_control(original,True)
    notice=next(node for node in walk(wrapped) if node.event_triggers.get("on_click") and "show_locked_test_view_mode" in str(node.event_triggers))
    frozen=notice.children[0]
    assert frozen.disabled is True
    assert not frozen.event_triggers
    assert "#E5E7EB" in str(frozen.style)
    assert "start_replacing_qp" not in str(notice.event_triggers)
    assert "pointerEvents" in str(frozen.style) or "pointer_events" in str(frozen.style)
    assert original.event_triggers.get("on_click") is not None
    assert original.disabled is not True

def test_locked_upload_freezes_nested_browse_button():
    upload=rx.box(rx.button("Browse",on_click=rx.console_log("browse")))
    wrapped=locked_control(upload,True)
    notice=next(node for node in walk(wrapped) if "show_locked_test_view_mode" in str(node.event_triggers))
    assert all(not node.event_triggers for node in walk(notice.children[0]))

def test_view_only_notice_supports_keyboard_without_editing():
    root=rx.State(_reflex_internal_init=True)
    import asyncio
    state=asyncio.run(root.get_state(FacilitatorState))
    assert state.show_locked_test_view_mode_key("Tab") is None
    assert "View mode only" in str(state.show_locked_test_view_mode_key("Enter"))
    assert "View mode only" in str(state.show_locked_test_view_mode())

def test_mutation_controls_have_locked_presentation_and_views_remain_enabled():
    path=Path(__file__).parent/'ai_hybrid_evaluator/pages/facilitator/assessment_workspace.py'
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    wrappers=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and ast.unparse(node.func)=='locked_control']
    assert len(wrappers)>=35
    text='\n'.join(ast.unparse(node) for node in wrappers)
    for action in ['start_replacing_qp','facilitator_remove_test','open_candidate_test_status','save_manual_evaluation','save_review_row','save_weightage']:
        assert action in text
    assert 'open_qp_preview' not in text


def test_locked_menu_retains_menu_structure_and_only_notice_action():
    component=rx.menu.item("Delete", on_click=FacilitatorState.facilitator_remove_test("Formative 1"), disabled=FacilitatorState.is_selected_test_locked)
    control=locked_control(component,True)
    menu=rx.menu.content(control)
    notices=[node for node in walk(menu) if "show_locked_test_view_mode" in str(node.event_triggers)]
    assert notices
    assert all("facilitator_remove_test" not in str(node.event_triggers) for node in notices)
