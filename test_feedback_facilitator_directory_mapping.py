from pathlib import Path
from types import SimpleNamespace

from backend.services.feedback_service import FeedbackService


def test_feedback_view_uses_persisted_facilitator_name(monkeypatch):
    class PersistedFacilitatorDirectory:
        def __init__(self, _path):
            pass

        def get_all(self):
            return [
                {
                    "emp_id": "F002",
                    "name": "P Vagheswara Subramanian",
                    "email": "vaghi@example.com",
                    "phone": "0000000000",
                    "password": "unused-test-password",
                }
            ]

    monkeypatch.setattr(
        "backend.services.feedback_service.FacilitatorRepository",
        PersistedFacilitatorDirectory,
    )

    service = FeedbackService.__new__(FeedbackService)
    service.assignments = SimpleNamespace(
        repository=SimpleNamespace(
            file_path=Path("backend/data/test_candidates.json")
        ),
        candidates=SimpleNamespace(list_candidates=lambda: []),
    )
    service.assessments = SimpleNamespace(
        repository=SimpleNamespace(
            get_all=lambda: [{"assessment_id": "assessment-1", "name": "HoQ 2"}]
        ),
        tests=SimpleNamespace(repository=SimpleNamespace(get_all=lambda: [])),
        _facilitators=lambda: [
            {"emp_id": "F002", "name": "Meena Iyer"},
        ],
    )
    service.forms = SimpleNamespace(
        get_all=lambda: [
            {
                "feedback_form_id": "form-1",
                "title": "Facilitator Feedback",
                "questions": [],
            }
        ]
    )
    service.responses = SimpleNamespace(
        get_all=lambda: [
            {
                "feedback_response_id": "response-1",
                "feedback_form_id": "form-1",
                "respondent_role": "facilitator",
                "facilitator_id": "F002",
                "candidate_id": None,
                "assessment_id": "assessment-1",
                "test_id": None,
                "answers": {},
            }
        ]
    )

    views = service.response_views()

    assert views[0]["facilitator"] == "P Vagheswara Subramanian"
