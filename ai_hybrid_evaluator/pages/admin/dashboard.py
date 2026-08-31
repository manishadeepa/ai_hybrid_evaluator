"""Admin dashboard overview — stat cards summarizing the whole system."""

import reflex as rx
from ai_hybrid_evaluator.components.layout.dashboard_shell import admin_shell
from ai_hybrid_evaluator.components.dashboard.stat_card import stat_card
from ai_hybrid_evaluator.state.admin_state import AdminState
from ai_hybrid_evaluator.theme import COLORS


def admin_dashboard_page() -> rx.Component:
    content = rx.grid(
        stat_card("Total Facilitators", AdminState.total_facilitators, "user-cog", COLORS["primary"], COLORS["primary_soft"]),
        stat_card("Total Candidates", AdminState.total_candidates, "users", "#0E9F6E", "#E6F7F1"),
        stat_card("Active Assessments", AdminState.active_assessments, "file-text", "#C9973B", "#FBF3E4"),
        stat_card("Pending Evaluations", AdminState.pending_evaluations, "clock", COLORS["danger"], "#FEF3F2"),
        columns="4",
        spacing="4",
        width="100%",
    )
    return admin_shell(
        active="dashboard",
        title="Dashboard",
        subtitle="Overview of facilitators, candidates, and assessments.",
        content=content,
    )