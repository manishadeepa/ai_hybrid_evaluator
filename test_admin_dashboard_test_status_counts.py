from ai_hybrid_evaluator.state.admin_state import count_assessments_by_status


def test_dashboard_counts_assessment_assignments_from_approval_and_close_state():
    assessments = [
        {"tests": ["Formative 1", "Formative 2"], "approval_status": "approved", "status": "In Progress"},
        {
            "tests": ["Formative 3"],
            "approval_status": "pending",
            "facilitator_approvals": {"F001": "approved", "F002": "pending"},
            "status": "Scheduled",
        },
        {"tests": ["Final 1", "Final 2", "Final 3"], "approval_status": "approved", "status": "Completed"},
        {"tests": [], "approval_status": "approved", "status": "In Progress"},
    ]

    assert count_assessments_by_status(assessments) == {
        "in_progress": 2,
        "pending": 1,
        "completed": 1,
    }


def test_dashboard_counts_assignments_without_test_multiplication():
    assessments = [
        {"tests": ["Formative 1"], "final_test": "Summative", "approval_status": "approved"},
        {
            "test_ids": {"Legacy 1": "t1", "Legacy 2": "t2"},
            "status": "Draft",
            "facilitator_approvals": {"F001": "approved"},
        },
    ]

    assert count_assessments_by_status(assessments) == {
        "in_progress": 2,
        "pending": 0,
        "completed": 0,
    }
