"""Shared white card shell, centered on the light canvas background."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS


def auth_card(content: rx.Component) -> rx.Component:
    return rx.center(
        rx.box(
            content,
            background=COLORS["surface"],
            border=f"1px solid {COLORS['line']}",
            border_radius="16px",
            box_shadow="0 4px 24px rgba(16, 24, 40, 0.08)",
            padding="2.75em 2.5em",
            width="420px",
        ),
        width="100%",
        min_height="100vh",
        background=COLORS["canvas"],
        padding="2em",
    )