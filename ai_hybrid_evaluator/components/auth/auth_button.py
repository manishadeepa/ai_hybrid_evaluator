"""Primary indigo action button — consistent across sign in / sign up."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def auth_button(label: str, on_click) -> rx.Component:
    return rx.button(
        label,
        on_click=on_click,
        width="100%",
        size="3",
        height="44px",
        border_radius="10px",
        background=COLORS["primary"],
        color="white",
        font_family=FONT_BODY,
        weight="bold",
        cursor="pointer",
        _hover={"background": COLORS["primary_hover"]},
    )