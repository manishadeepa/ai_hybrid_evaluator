"""
Unified Top Header for GenAI Hybrid Evaluator — used across Admin, Facilitator, and Candidate.
Features TVS logo on left, centered brand title with sparkle accents, and user profile avatar on right.
"""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def unified_topbar(
    user_name: str = "Welcome, Admin",
    role_name: str = "Administrator",
    avatar_initial: str = "A",
) -> rx.Component:
    return rx.hstack(
        # ── Left: TVS Brand Logo ──────────────────────────────────────────
        rx.hstack(
            rx.image(
                src="/tvs_logo.png",
                height="34px",
                width="auto",
                object_fit="contain",
            ),
            align_items="center",
            min_width="220px",
        ),

        # ── Center: Brand Title with Decorative Accents ───────────────────
        rx.hstack(
            rx.box(
                width="40px",
                height="2px",
                background="linear-gradient(90deg, transparent, #8B5CF6)",
                display=["none", "none", "block"],
            ),
            rx.icon("sparkle", size=16, color="#8B5CF6"),
            rx.text(
                "GEN AI HYBRID EVALUATOR",
                font_family=FONT_BODY,
                size="4",
                weight="bold",
                letter_spacing="0.05em",
                color=COLORS["ink"],
                white_space="nowrap",
            ),
            rx.icon("sparkle", size=16, color="#8B5CF6"),
            rx.box(
                width="40px",
                height="2px",
                background="linear-gradient(90deg, #8B5CF6, transparent)",
                display=["none", "none", "block"],
            ),
            spacing="3",
            align_items="center",
            justify_content="center",
            flex="1",
        ),

        # ── Right: User Profile Avatar & Role ─────────────────────────────
        rx.hstack(
            rx.box(
                rx.text(
                    avatar_initial,
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color="#6D28D9",
                ),
                background="#EDE9FE",
                width="36px",
                height="36px",
                border_radius="50%",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    user_name,
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color=COLORS["ink"],
                    white_space="nowrap",
                ),
                rx.text(
                    role_name,
                    font_family=FONT_BODY,
                    size="1",
                    color=COLORS["slate"],
                    white_space="nowrap",
                ),
                spacing="0",
                align_items="start",
            ),
            rx.icon("chevron-down", size=14, color=COLORS["slate"]),
            spacing="3",
            align_items="center",
            min_width="220px",
            justify_content="end",
        ),

        width="100%",
        height="64px",
        padding="0 2em",
        border_bottom=f"1px solid {COLORS['line']}",
        background=COLORS["surface"],
        align_items="center",
        justify_content="space-between",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.03)",
        z_index="20",
    )


def topbar(title: str = "", subtitle: str = "") -> rx.Component:
    """Default Admin topbar wrapper for backward-compatibility."""
    return unified_topbar(
        user_name="Welcome, Admin",
        role_name="Administrator",
        avatar_initial="A",
    )