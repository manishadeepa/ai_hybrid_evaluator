"""Shared shell — sidebar + top bar + content area. Every admin page is wrapped in this."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.sidebar import sidebar
from ai_hybrid_evaluator.components.layout.topbar import topbar
from ai_hybrid_evaluator.theme import COLORS


def admin_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(active),
        rx.vstack(
            topbar(title, subtitle),
            rx.box(content, padding="2em", width="100%"),
            spacing="0",
            width="100%",
            height="100vh",
            overflow_y="auto",
            background=COLORS["canvas"],
        ),
        spacing="0",
        width="100%",
        height="100vh",
    )