"""Labeled input — visible border, strong text contrast, clear focus ring."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def auth_input(
    label: str,
    placeholder: str,
    value,
    on_change,
    input_type: str = "text",
    on_key_down=None,
) -> rx.Component:
    extra_props = {}
    if on_key_down is not None:
        extra_props["on_key_down"] = on_key_down

    return rx.vstack(
        rx.text(
            label,
            font_family=FONT_BODY,
            size="2",
            weight="medium",
            color=COLORS["ink"],
        ),
        rx.input(
            placeholder=placeholder,
            type=input_type,
            value=value,
            on_change=on_change,
            width="100%",
            size="3",
            color=COLORS["ink"],
            background=COLORS["surface"],
            border=f"1.5px solid {COLORS['line']}",
            border_radius="10px",
            style={"::placeholder": {"color": COLORS["placeholder"]}},
            _focus={
                "border_color": COLORS["primary"],
                "box_shadow": f"0 0 0 3px {COLORS['primary_soft']}",
                "outline": "none",
            },
            **extra_props,
        ),
        spacing="1",
        align_items="start",
        width="100%",
    )