"""Reusable stat card — used on the dashboard overview (Total Facilitators, etc.)."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def stat_card(label: str, value, icon: str, accent: str, soft: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(icon, size=20, color=accent),
            background=soft,
            border_radius="10px",
            padding="0.7em",
        ),
        rx.vstack(
            rx.text(label, font_family=FONT_BODY, size="2", color=COLORS["slate"]),
            rx.text(value, font_family=FONT_BODY, size="6", weight="bold", color=COLORS["ink"]),
            spacing="0",
            align_items="start",
        ),
        spacing="3",
        align_items="center",
        background=COLORS["surface"],
        border=f"1px solid {COLORS['line']}",
        border_radius="12px",
        padding="1.3em",
        width="100%",
    )
    