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
    {"name": "Priya Sharma", "emp_id": "CAND-2031", "email": "priya.sharma@genaievaluator.com", "password": "Priya@123"},
    {"name": "Arjun Rao", "emp_id": "CAND-2054", "email": "arjun.rao@genaievaluator.com", "password": "Arjun@123"},
    {"name": "Divya Nair", "emp_id": "CAND-2061", "email": "divya.nair@genaievaluator.com", "password": "Divya@123"},
]

SHARED_FACILITATORS: list[Facilitator] = [ 
    {
        "name": "Ravi Kumar",
        "emp_id": "F001",
        "email": "ravi.kumar@genaievaluator.com",
        "phone": "9876543210",
        "password": "Ravi@123",
    },
    {
        "name": "Meena Iyer",
        "emp_id": "F002",
        "email": "meena.iyer@genaievaluator.com",
        "phone": "9876500000",
        "password": "Meena@123",
    },
]


class TestItem(TypedDict, total=False):
    name: str
    date: str
    is_final: bool
    test_id: str
    has_qp: bool
    qp_filename: str


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