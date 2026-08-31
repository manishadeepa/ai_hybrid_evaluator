"""Logo + app name + page heading + description — reused on sign in / sign up."""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY


def auth_header(heading: str, subheading: str) -> rx.Component:
    return rx.vstack(
        rx.center(
            rx.image(src="/tvs_logo.png", width="40px", height="40px", object_fit="contain"),
            width="100%",
            padding_bottom="0.6em",
        ),
        rx.center(
            rx.text(
                "GenAI Hybrid Evaluator",
                font_family=FONT_BODY,
                weight="bold",
                size="4",
                color=COLORS["primary"],
            ),
            width="100%",
        ),
        rx.center(
            rx.heading(
                heading,
                font_family=FONT_BODY,
                size="6",
                weight="bold",
                color=COLORS["ink"],
                padding_top="1.1em",
            ),
            width="100%",
        ),
        rx.center(
            rx.text(
                subheading,
                font_family=FONT_BODY,
                size="2",
                color=COLORS["slate"],
                text_align="center",
                padding_top="0.4em",
            ),
            width="100%",
        ),
        align_items="center",
        width="100%",
        padding_bottom="2em",
    )