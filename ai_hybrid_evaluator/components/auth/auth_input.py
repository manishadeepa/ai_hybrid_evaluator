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
    show_password=None,
    on_toggle_password=None,
) -> rx.Component:
    extra_props = {}
    if on_key_down is not None:
        extra_props["on_key_down"] = on_key_down

    slots = []
    actual_type = input_type
    if show_password is not None and on_toggle_password is not None:
        actual_type = rx.cond(show_password, "text", "password")
        slots.append(
            rx.input.slot(
                rx.icon_button(
                    rx.cond(
                        show_password,
                        rx.icon("eye-off", size=18),
                        rx.icon("eye", size=18),
                    ),
                    size="1",
                    variant="ghost",
                    color=COLORS["slate"],
                    cursor="pointer",
                    type="button",
                    tab_index=-1,
                    on_click=on_toggle_password,
                    _hover={"color": COLORS["ink"], "background": "transparent"},
                    style={
                        "background": "transparent",
                        "border": "none",
                        "box_shadow": "none",
                        "padding": "0",
                    },
                ),
                side="right",
            )
        )

    return rx.vstack(
        rx.text(
            label,
            font_family=FONT_BODY,
            size="2",
            weight="medium",
            color=COLORS["ink"],
        ),
        rx.input(
            *slots,
            placeholder=placeholder,
            type=actual_type,
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