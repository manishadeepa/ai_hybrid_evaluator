"""Grey, non-mutating controls with an accessible view-only explanation."""
from copy import deepcopy
import reflex as rx
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState

LOCKED_MESSAGE = "View mode only. This test is locked."
GREY_STYLE = {
    "background": "#E5E7EB !important", "color": "#667085 !important",
    "border_color": "#D0D5DD !important", "opacity": "1", "cursor": "not-allowed",
}

def _keyboard_key(event: rx.Var[dict[str, str]]):
    return [event["key"]]

class _ViewOnlyNotice(type(rx.el.div())):
    on_key_down: rx.EventHandler[_keyboard_key]

def _freeze_component(component):
    component.event_triggers = {}
    if hasattr(component, "disabled"):
        component.disabled = True
    component.style.update({**GREY_STYLE, "pointer_events": "none",
        "_hover": GREY_STYLE, "_disabled": GREY_STYLE,
        "& *": {"color": "#667085 !important", "pointer_events": "none"}})
    for child in component.children:
        if isinstance(child, rx.Component):
            _freeze_component(child)

def locked_control(component: rx.Component, locked) -> rx.Component:
    """Keep read-only notices clickable while native modifying controls stay disabled."""
    component.style.update({"_disabled": GREY_STYLE})
    frozen = deepcopy(component)
    _freeze_component(frozen)
    if component.__class__.__name__ == "DropdownMenuItem":
        # Menu items must stay direct descendants of their menu content.
        # Their only locked-state action is the informational notice.
        frozen.disabled = False
        frozen.style.update({"pointer_events": "auto"})
        frozen.event_triggers = rx.menu.item("", on_click=FacilitatorState.show_locked_test_view_mode).event_triggers
        frozen.custom_attrs["aria-label"] = LOCKED_MESSAGE
        return rx.cond(locked, frozen, component)
    layout = {key: component.style[key] for key in ("width", "min_width", "max_width", "flex", "flex_grow", "align_self") if key in component.style}
    notice = _ViewOnlyNotice.create(
        frozen, title=LOCKED_MESSAGE,
        role="button", tab_index=0, aria_disabled=True, aria_label=LOCKED_MESSAGE,
        on_click=FacilitatorState.show_locked_test_view_mode,
        on_key_down=FacilitatorState.show_locked_test_view_mode_key,
        style={"display": "inline-flex", "cursor": "not-allowed", **layout},
    )
    return rx.cond(locked, notice, component)
