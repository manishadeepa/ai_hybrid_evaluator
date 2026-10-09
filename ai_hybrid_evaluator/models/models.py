"""
Typed models for mock frontend data.
"""

from pathlib import Path
from typing import TypedDict

from backend.repositories.json_repository import JSONRepository


class Candidate(TypedDict):
    name: str
    emp_id: str
    email: str
    password: str

class Facilitator(TypedDict):
    name: str
    emp_id: str
    email: str
    phone: str
    password: str


# ─────────────────────────────────────────────────────────────
# Shared in-memory data stores (persists across sessions/tabs)
# ─────────────────────────────────────────────────────────────

SHARED_CANDIDATES: list[Candidate] = [
    {"name": "Priya Sharma", "emp_id": "CAND-2031", "email": "priya.sharma@tvsmotor.com", "password": "Priya@123"},
    {"name": "Arjun Rao", "emp_id": "CAND-2054", "email": "arjun.rao@tvsmotor.com", "password": "Arjun@123"},
    {"name": "Divya Nair", "emp_id": "CAND-2061", "email": "divya.nair@tvsmotor.com", "password": "Divya@123"},
]

SHARED_FACILITATORS: list[Facilitator] = [ 
    {
        "name": "Ravi Kumar",
        "emp_id": "F001",
        "email": "ravi.kumar@tvsmotor.com",
        "phone": "9876543210",
        "password": "Ravi@123",
    },
    {
        "name": "Meena Iyer",
        "emp_id": "F002",
        "email": "meena.iyer@tvsmotor.com",
        "phone": "9876500000",
        "password": "Meena@123",
    },
]

# Profile details are stored independently from login credentials and keyed by account ID.
_PROFILE_DATA_DIR = Path(__file__).resolve().parents[2] / "backend" / "data"
FACILITATOR_PROFILE_FILE = _PROFILE_DATA_DIR / "facilitator_profiles.json"
CANDIDATE_PROFILE_FILE = _PROFILE_DATA_DIR / "candidate_profiles.json"


def _profile_defaults(emp_id: str, identity: dict, optional_fields: tuple[str, ...]) -> dict:
    profile = {
        "emp_id": emp_id,
        "full_name": identity.get("full_name", ""),
        "email": identity.get("email", ""),
        "phone": identity.get("phone", ""),
        "profile_photo_url": "",
    }
    profile.update({field: "" for field in optional_fields})
    return profile


def _get_profile(file_path: Path, emp_id: str, defaults: dict) -> dict:
    if not emp_id:
        return dict(defaults)
    records = JSONRepository(file_path).get_all()
    matches = [row for row in records if str(row.get("emp_id", "")).casefold() == emp_id.casefold()]
    if len(matches) > 1:
        raise ValueError(f"Duplicate profile records found for {emp_id}.")
    return {**defaults, **matches[0]} if matches else dict(defaults)


def _save_profile(file_path: Path, emp_id: str, data: dict) -> dict:
    identity = str(emp_id or "").strip()
    if not identity:
        raise ValueError("A profile cannot be saved without an account ID.")
    repository = JSONRepository(file_path)
    records = repository.get_all()
    match_index = next(
        (i for i, row in enumerate(records) if str(row.get("emp_id", "")).casefold() == identity.casefold()),
        None,
    )
    updated = dict(records[match_index]) if match_index is not None else {"emp_id": identity}
    updated.update(data)
    updated["emp_id"] = identity
    if match_index is None:
        records.append(updated)
    else:
        records[match_index] = updated
    repository.save_all(records)
    return dict(updated)


def get_facilitator_profile(emp_id: str, default_name: str = "", default_email: str = "", default_phone: str = "") -> dict:
    """Load a facilitator profile from JSON, using account identity for first-load defaults."""
    defaults = _profile_defaults(
        emp_id,
        {"full_name": default_name, "email": default_email, "phone": default_phone},
        ("location", "designation", "department", "business_unit", "years_experience",
         "primary_expertise", "specific_skills", "highest_qualification", "specialization",
         "certifications", "training_experience", "assessment_experience", "subjects_domains",
         "assessment_types", "availability"),
    )
    return _get_profile(FACILITATOR_PROFILE_FILE, emp_id, defaults)


def save_facilitator_profile(emp_id: str, data: dict):
    """Persist facilitator profile fields in backend/data/facilitator_profiles.json."""
    return _save_profile(FACILITATOR_PROFILE_FILE, emp_id, data)


def get_candidate_profile(emp_id: str, default_name: str = "", default_email: str = "", default_phone: str = "") -> dict:
    """Load a candidate profile from JSON, using account identity for first-load defaults."""
    defaults = _profile_defaults(
        emp_id,
        {"full_name": default_name, "email": default_email, "phone": default_phone},
        ("location", "date_of_joining", "employment_status", "company_bu", "department",
         "designation", "grade_level", "reporting_manager", "work_location"),
    )
    return _get_profile(CANDIDATE_PROFILE_FILE, emp_id, defaults)


def save_candidate_profile(emp_id: str, data: dict):
    """Persist candidate profile fields in backend/data/candidate_profiles.json."""
    return _save_profile(CANDIDATE_PROFILE_FILE, emp_id, data)


class TestItem(TypedDict, total=False):
    name: str
    date: str
    is_final: bool
    test_id: str
    has_qp: bool
    qp_filename: str
    weightage: str
    has_score: bool
    norm_score_str: str
    weighted_score_str: str


class Assessment(TypedDict, total=False):
    assessment_date: str
    start_date: str
    end_date: str
    assessment_id: str
    test_ids: dict[str, str]
    test_descriptions: dict[str, str]
    name: str
    # Multi-facilitator fields (primary)
    facilitator_ids: list[str]
    facilitator_names: list[str]
    # Legacy single-value aliases (kept for backward compat — always equals first in list)
    facilitator_id: str
    facilitator_name: str
    assigned_candidates: list[str]
    status: str
    tests: list[str]
    final_test: str
    # "pending" | "approved" | "declined"  (set by facilitator)
    approval_status: str
    facilitator_approvals: dict[str, str]
    test_dates: dict[str, str]
    test_timings: dict[str, dict[str, str]]
    question_papers: dict[str, str]


class CandidateSummary(TypedDict):
    name: str
    emp_id: str
    email: str


class AssessmentDetail(TypedDict):
    """Assessment enriched with resolved candidate objects (for Facilitator views)."""
    assessment_id: str
    name: str
    # Multi-facilitator fields
    facilitator_ids: list[str]
    facilitator_names: list[str]
    # Legacy aliases
    facilitator_id: str
    facilitator_name: str
    assigned_candidates: list[str]
    status: str
    tests: list[str]
    final_test: str
    all_tests: list[str]
    candidate_details: list[CandidateSummary]
    # "pending" | "approved" | "declined"  (set by facilitator)
    approval_status: str
    facilitator_approvals: dict[str, str]
    test_dates: dict[str, str]
    test_items: list[TestItem]
    assessment_date: str
