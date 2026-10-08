from ai_hybrid_evaluator.state.admin_state import count_assessment_tests_by_status


def test_dashboard_counts_tests_from_approval_and_close_state():
    assessments = [
        {"tests": ["Formative 1", "Formative 2"], "approval_status": "approved", "status": "In Progress"},
        {"tests": ["Formative 3"], "approval_status": "pending", "status": "Scheduled"},
        {"tests": ["Final"], "approval_status": "approved", "status": "Completed"},
        {"tests": [], "approval_status": "approved", "status": "In Progress"},
    ]

    assert count_assessment_tests_by_status(assessments) == {
        "in_progress": 2,
        "pending": 1,
        "completed": 1,
    }


def test_dashboard_counts_final_tests_and_legacy_test_id_maps():
    assessments = [
        {"tests": ["Formative 1"], "final_test": "Summative", "approval_status": "approved"},
        {"test_ids": {"Legacy 1": "t1", "Legacy 2": "t2"}, "status": "Draft"},
    ]

    assert count_assessment_tests_by_status(assessments) == {
        "in_progress": 2,
        "pending": 2,
        "completed": 0,
    }
