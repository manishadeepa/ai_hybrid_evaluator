"""Shared shell for Admin pages — full-width unified top bar + clean white sidebar + content area."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.sidebar import sidebar
from ai_hybrid_evaluator.components.layout.topbar import unified_topbar
from ai_hybrid_evaluator.theme import COLORS


def admin_shell(active: str, title: str, subtitle: str, content: rx.Component) -> rx.Component:
    return rx.vstack(
        # Full-width Top Header
        unified_topbar(
            user_name="Welcome, Admin",
            role_name="Administrator",
            avatar_initial="A",
        ),
        # Body: Sidebar + Main Content Area
        rx.hstack(
            sidebar(active),
            rx.box(
                content,
                padding="2em",
                width="100%",
                height="calc(100vh - 64px)",
                overflow_y="auto",
                background=COLORS["canvas"],
            ),
            spacing="0",
            width="100%",
            flex="1",
            overflow="hidden",
        ),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        background=COLORS["canvas"],
    )