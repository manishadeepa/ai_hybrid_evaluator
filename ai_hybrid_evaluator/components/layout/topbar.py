"""Top bar — page title, subtitle, and the logged-in admin's name."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def topbar(title: str, subtitle: str) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="5", weight="bold", font_family=FONT_BODY, color=COLORS["ink"]),
            rx.text(subtitle, size="2", color=COLORS["slate"], font_family=FONT_BODY),
            spacing="0",
            align_items="start",
        ),
        rx.spacer(),
        rx.text("Welcome, Admin", font_family=FONT_BODY, size="2", weight="medium", color=COLORS["ink"]),
        width="100%",
        padding="1.4em 2em",
        border_bottom=f"1px solid {COLORS['line']}",
        background=COLORS["surface"],
        align_items="center",
    )