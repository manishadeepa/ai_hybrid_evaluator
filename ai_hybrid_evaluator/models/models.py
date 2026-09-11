"""
Typed models for mock frontend data.
"""

from typing import TypedDict


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

# ─────────────────────────────────────────────────────────────
# Shared Profiles Store (linked by Facilitator ID / Candidate ID)
# ─────────────────────────────────────────────────────────────

SHARED_FACILITATOR_PROFILES: dict[str, dict] = {
    "F001": {
        "emp_id": "F001",
        "full_name": "Ravi Kumar",
        "email": "ravi.kumar@tvsmotor.com",
        "phone": "9876543210",
        "location": "Hosur, Tamil Nadu",
        "profile_photo_url": "",
        "designation": "Lead Evaluator",
        "department": "Quality Assurance",
        "business_unit": "Two-Wheeler Operations",
        "years_experience": "10",
        "primary_expertise": "Domain Specific",
        "specific_skills": "Quality Control, Six Sigma, GD&T",
        "highest_qualification": "Master's Degree",
        "specialization": "Mechanical Engineering",
        "certifications": "Certified Quality Auditor, Six Sigma Black Belt",
        "training_experience": "10+ years",
        "assessment_experience": "8 years",
        "subjects_domains": "Quality Assurance & Testing",
        "assessment_types": "Technical & Practical",
        "availability": "Weekdays 9 AM - 6 PM IST",
    },
    "F002": {
        "emp_id": "F002",
        "full_name": "Meena Iyer",
        "email": "meena.iyer@tvsmotor.com",
        "phone": "9876500000",
        "location": "Bangalore, Karnataka",
        "profile_photo_url": "",
        "designation": "Senior Evaluator",
        "department": "Research & Development (R&D)",
        "business_unit": "EV & Technology",
        "years_experience": "7",
        "primary_expertise": "Technical Interviews",
        "specific_skills": "Battery Management Systems, Embedded C",
        "highest_qualification": "Master's Degree",
        "specialization": "Electrical and Electronics",
        "certifications": "EV Powertrain Certification",
        "training_experience": "6-10 years",
        "assessment_experience": "5 years",
        "subjects_domains": "Electric Vehicles (EV) & Battery Tech",
        "assessment_types": "Technical Interviews",
        "availability": "Weekdays 10 AM - 5 PM IST",
    },
}

SHARED_CANDIDATE_PROFILES: dict[str, dict] = {
    "CAND-2031": {
        "emp_id": "CAND-2031",
        "full_name": "Priya Sharma",
        "email": "priya.sharma@tvsmotor.com",
        "phone": "+91 98765 43210",
        "location": "Bangalore, India",
        "profile_photo_url": "",
        "date_of_joining": "2024-06-15",
        "employment_status": "Active",
        "company_bu": "TVS Motor Company",
        "department": "Quality Assurance & Testing",
        "designation": "Senior Quality Engineer",
        "grade_level": "L3 - Senior Associate",
        "reporting_manager": "Ravi Kumar (Lead Evaluator)",
        "work_location": "TVS Motor Plant, Hosur Facility, Block C",
    },
    "CAND-2054": {
        "emp_id": "CAND-2054",
        "full_name": "Arjun Rao",
        "email": "arjun.rao@tvsmotor.com",
        "phone": "+91 98765 43211",
        "location": "Hosur, India",
        "profile_photo_url": "",
        "date_of_joining": "2023-11-01",
        "employment_status": "Active",
        "company_bu": "TVS Motor Company",
        "department": "Manufacturing & Production",
        "designation": "Manufacturing Specialist",
        "grade_level": "L2 - Professional",
        "reporting_manager": "Ravi Kumar (Lead Evaluator)",
        "work_location": "TVS Motor Plant, Hosur Facility, Block A",
    },
    "CAND-2061": {
        "emp_id": "CAND-2061",
        "full_name": "Divya Nair",
        "email": "divya.nair@tvsmotor.com",
        "phone": "+91 98765 43212",
        "location": "Bangalore, India",
        "profile_photo_url": "",
        "date_of_joining": "2024-01-10",
        "employment_status": "Active",
        "company_bu": "TVS Motor Company",
        "department": "Research & Development (R&D)",
        "designation": "Associate Quality Engineer",
        "grade_level": "L1 - Associate",
        "reporting_manager": "Meena Iyer (Senior Evaluator)",
        "work_location": "TVS R&D Center, Hosur",
    },
}


def get_facilitator_profile(emp_id: str, default_name: str = "", default_email: str = "", default_phone: str = "") -> dict:
    """Retrieve facilitator profile by Facilitator ID, initializing defaults if needed."""
    if emp_id in SHARED_FACILITATOR_PROFILES:
        return dict(SHARED_FACILITATOR_PROFILES[emp_id])
    prof = {
        "emp_id": emp_id,
        "full_name": default_name or "Facilitator",
        "email": default_email,
        "phone": default_phone,
        "location": "Hosur, Tamil Nadu",
        "profile_photo_url": "",
        "designation": "Evaluator",
        "department": "Quality Assurance",
        "business_unit": "Two-Wheeler Operations",
        "years_experience": "3",
        "primary_expertise": "Technical Interviews",
        "specific_skills": "Evaluation, Domain Expertise",
        "highest_qualification": "Bachelor's Degree",
        "specialization": "Mechanical Engineering",
        "certifications": "",
        "training_experience": "3-5 years",
        "assessment_experience": "2 years",
        "subjects_domains": "General Technical",
        "assessment_types": "Technical",
        "availability": "Weekdays 9 AM - 5 PM IST",
    }
    SHARED_FACILITATOR_PROFILES[emp_id] = prof
    return dict(prof)


def save_facilitator_profile(emp_id: str, data: dict):
    """Save or update facilitator profile in shared store."""
    if emp_id not in SHARED_FACILITATOR_PROFILES:
        SHARED_FACILITATOR_PROFILES[emp_id] = get_facilitator_profile(emp_id)
    SHARED_FACILITATOR_PROFILES[emp_id].update(data)


def get_candidate_profile(emp_id: str, default_name: str = "", default_email: str = "") -> dict:
    """Retrieve candidate profile by Candidate ID, initializing defaults if needed."""
    if emp_id in SHARED_CANDIDATE_PROFILES:
        return dict(SHARED_CANDIDATE_PROFILES[emp_id])
    prof = {
        "emp_id": emp_id,
        "full_name": default_name or "Candidate",
        "email": default_email,
        "phone": "",
        "location": "Bangalore, India",
        "profile_photo_url": "",
        "date_of_joining": "2024-01-01",
        "employment_status": "Active",
        "company_bu": "TVS Motor Company",
        "department": "Quality Assurance & Testing",
        "designation": "Quality Engineer",
        "grade_level": "L2 - Professional",
        "reporting_manager": "Ravi Kumar (Lead Evaluator)",
        "work_location": "TVS Motor Plant, Hosur Facility",
    }
    SHARED_CANDIDATE_PROFILES[emp_id] = prof
    return dict(prof)


def save_candidate_profile(emp_id: str, data: dict):
    """Save or update candidate profile in shared store."""
    if emp_id not in SHARED_CANDIDATE_PROFILES:
        SHARED_CANDIDATE_PROFILES[emp_id] = get_candidate_profile(emp_id)
    SHARED_CANDIDATE_PROFILES[emp_id].update(data)


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
    question_papers: dict[str, str]


class CandidateSummary(TypedDict):
    name: str
    emp_id: str
    email: str


class AssessmentDetail(TypedDict):
    """Assessment enriched with resolved candidate objects (for Facilitator views)."""
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
