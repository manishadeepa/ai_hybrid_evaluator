import json

from ai_hybrid_evaluator.models import models


def test_facilitator_profile_is_persisted_and_partial_saves_keep_other_fields(tmp_path, monkeypatch):
    profile_file = tmp_path / "facilitator_profiles.json"
    monkeypatch.setattr(models, "FACILITATOR_PROFILE_FILE", profile_file)

    initial = models.get_facilitator_profile(
        "F123", default_name="Casey Facilitator", default_email="casey@example.com", default_phone="5551234567"
    )
    assert initial["full_name"] == "Casey Facilitator"
    assert initial["email"] == "casey@example.com"
    assert initial["department"] == ""

    models.save_facilitator_profile("F123", {"department": "Engineering", "specific_skills": "Testing"})
    models.save_facilitator_profile("F123", {"location": "Hosur"})

    loaded = models.get_facilitator_profile("F123")
    assert loaded["department"] == "Engineering"
    assert loaded["specific_skills"] == "Testing"
    assert loaded["location"] == "Hosur"
    assert json.loads(profile_file.read_text(encoding="utf-8"))[0]["emp_id"] == "F123"


def test_candidate_profile_is_persisted_and_does_not_seed_mock_details(tmp_path, monkeypatch):
    profile_file = tmp_path / "candidate_profiles.json"
    monkeypatch.setattr(models, "CANDIDATE_PROFILE_FILE", profile_file)

    initial = models.get_candidate_profile(
        "CAND-9001", default_name="Jordan Candidate", default_email="jordan@example.com"
    )
    assert initial["full_name"] == "Jordan Candidate"
    assert initial["email"] == "jordan@example.com"
    assert initial["department"] == ""
    assert initial["date_of_joining"] == ""

    models.save_candidate_profile("CAND-9001", {"department": "Research", "work_location": "Hosur"})

    loaded = models.get_candidate_profile("CAND-9001")
    assert loaded["department"] == "Research"
    assert loaded["work_location"] == "Hosur"
    assert json.loads(profile_file.read_text(encoding="utf-8"))[0]["emp_id"] == "CAND-9001"
