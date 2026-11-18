"""Shared in-memory catalog data stores (persists across sessions/tabs)."""
from typing import TypedDict


class CandidateDict(TypedDict, total=False):
    name: str
    emp_id: str
    department: str
    email: str
    password: str


class FacilitatorDict(TypedDict):
    name: str
    emp_id: str
    email: str
    phone: str
    password: str


SHARED_CANDIDATES: list[CandidateDict] = []
SHARED_FACILITATORS: list[FacilitatorDict] = []
