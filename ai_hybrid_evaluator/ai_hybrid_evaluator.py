"""Main entry point — registers every page and route."""

import reflex as rx

from ai_hybrid_evaluator.pages.auth.login import login_page
from ai_hybrid_evaluator.pages.auth.signup import signup_page
from ai_hybrid_evaluator.pages.admin.dashboard import admin_dashboard_page
from ai_hybrid_evaluator.pages.admin.facilitators import facilitators_page
from ai_hybrid_evaluator.pages.admin.candidates import candidates_page
from ai_hybrid_evaluator.pages.admin.assessments import assessments_page
from ai_hybrid_evaluator.pages.admin.reports import reports_page
from ai_hybrid_evaluator.pages.admin.settings import settings_page
from ai_hybrid_evaluator.pages.admin.feedback import admin_feedback_page
from ai_hybrid_evaluator.state.admin_state import AdminFeedbackState
from ai_hybrid_evaluator.theme import FONT_STYLESHEETS
from ai_hybrid_evaluator.pages.auth.facilitator_login import facilitator_login_page
from ai_hybrid_evaluator.pages.facilitator.dashboard import facilitator_dashboard_page
from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import assessment_workspace_page
from ai_hybrid_evaluator.pages.facilitator.profile import facilitator_profile_page
from ai_hybrid_evaluator.pages.facilitator.feedback import facilitator_feedback_page
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorProfileState, FacilitatorState
from ai_hybrid_evaluator.state.candidate_state import CandidateState, CandidateProfileState
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.pages.candidate.candidate_login import candidate_login_page
from ai_hybrid_evaluator.pages.candidate.dashboard import candidate_dashboard_page
from ai_hybrid_evaluator.pages.candidate.candidate_test import candidate_test_page
from ai_hybrid_evaluator.pages.candidate.profile import candidate_profile_page

app = rx.App(
    stylesheets=FONT_STYLESHEETS,
    theme=rx.theme(
        appearance="light",
        accent_color="indigo",
        radius="large",
    ),
)


def index() -> rx.Component:
    return rx.fragment()


app.add_page(index, route="/", on_load=rx.redirect("/signin"))

# Admin Routes
app.add_page(login_page, route="/signin", title="Sign In", on_load=AuthState.on_signin_page_load)
app.add_page(signup_page, route="/signup", title="Sign Up")
app.add_page(admin_dashboard_page, route="/admin/dashboard", title="Admin Dashboard")
app.add_page(facilitators_page, route="/admin/facilitators", title="Facilitators")
app.add_page(candidates_page, route="/admin/candidates", title="Candidates")
app.add_page(assessments_page, route="/admin/assessments", title="Assessments")
app.add_page(reports_page, route="/admin/reports", title="Reports")
app.add_page(settings_page, route="/admin/settings", title="Settings")
app.add_page(admin_feedback_page, route="/admin/feedback", title="Feedback Management", on_load=AdminFeedbackState.on_load)

# Facilitator Routes
app.add_page(facilitator_login_page, route="/facilitator/signin", title="Facilitator Sign In")
app.add_page(facilitator_dashboard_page, route="/facilitator/dashboard", title="My Assessments")
app.add_page(assessment_workspace_page, route="/facilitator/assessment", title="Assessment Workspace")
app.add_page(facilitator_feedback_page, route="/facilitator/feedback", title="Feedback", on_load=FacilitatorState.on_feedback_page_load)
app.add_page(facilitator_profile_page, route="/facilitator/profile", title="My Profile", on_load=FacilitatorProfileState.load_profile)

# Candidate Routes
app.add_page(candidate_login_page, route="/candidate/login", title="Candidate Sign In")
app.add_page(candidate_login_page, route="/candidate/signin", title="Candidate Sign In")
app.add_page(candidate_dashboard_page, route="/candidate/dashboard", title="Candidate Dashboard", on_load=CandidateState.on_dashboard_load)
app.add_page(candidate_profile_page, route="/candidate/profile", title="My Profile", on_load=CandidateProfileState.load_profile)
app.add_page(candidate_test_page, route="/candidate/test", title="Test Environment", on_load=CandidateState.on_test_page_load)