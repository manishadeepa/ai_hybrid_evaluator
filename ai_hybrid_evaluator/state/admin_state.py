"""
Admin dashboard state — mock data only (frontend-only).
Backend developer will later swap the mock lists for real DB-backed queries,
and the add_*/update_*/delete_* functions for real API calls. Function names/
shapes kept stable on purpose so that swap is easy later.
"""

import json
from pathlib import Path
import re
import reflex as rx

from ai_hybrid_evaluator.models.models import (
    Candidate, Facilitator, Assessment,
    SHARED_CANDIDATES, SHARED_FACILITATORS,
    get_facilitator_profile, get_candidate_profile,
)

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
FACILITATOR_ID_REGEX = r"^F\d{3}$"
PHONE_REGEX = r"^\d{10}$"


class AdminState(rx.State):
    # ---- Sidebar UI state ----
    users_menu_open: bool = True

    def toggle_users_menu(self):
        self.users_menu_open = not self.users_menu_open

    # ---- Mock data ----
    facilitators: list[Facilitator] = list(SHARED_FACILITATORS)
    candidates: list[Candidate] = list(SHARED_CANDIDATES)
    active_assessments: int = 3
    pending_evaluations: int = 12

    # =========================================================
    # VIEW FACILITATOR PROFILE (dialog)
    # =========================================================
    show_view_facilitator_profile: bool = False
    viewing_facilitator_profile: dict = {}

    def open_view_facilitator_profile(self, index: int):
        if 0 <= index < len(self.facilitators):
            f = self.facilitators[index]
            fid = f["emp_id"]
            prof = get_facilitator_profile(
                fid,
                default_name=f.get("name", ""),
                default_email=f.get("email", ""),
                default_phone=f.get("phone", ""),
            )
            self.viewing_facilitator_profile = prof
            self.show_view_facilitator_profile = True

    def close_view_facilitator_profile(self):
        self.show_view_facilitator_profile = False

    def set_show_view_facilitator_profile(self, value: bool):
        self.show_view_facilitator_profile = value

    # =========================================================
    # VIEW CANDIDATE PROFILE (dialog)
    # =========================================================
    show_view_candidate_profile: bool = False
    viewing_candidate_profile: dict = {}

    def open_view_candidate_profile(self, index: int):
        if 0 <= index < len(self.candidates):
            c = self.candidates[index]
            cid = c["emp_id"]
            prof = get_candidate_profile(
                cid,
                default_name=c.get("name", ""),
                default_email=c.get("email", ""),
            )
            self.viewing_candidate_profile = prof
            self.show_view_candidate_profile = True

    def close_view_candidate_profile(self):
        self.show_view_candidate_profile = False

    def set_show_view_candidate_profile(self, value: bool):
        self.show_view_candidate_profile = value

    # ---- Computed stats ----
    @rx.var
    def total_facilitators(self) -> int:
        return len(self.facilitators)

    @rx.var
    def total_candidates(self) -> int:
        return len(self.candidates)

    # =========================================================
    # ADD FACILITATOR (dialog/form)
    # =========================================================
    show_add_facilitator: bool = False
    new_facilitator_empid: str = ""
    new_facilitator_name: str = ""
    new_facilitator_email: str = ""
    new_facilitator_phone: str = ""
    new_facilitator_password: str = ""
    facilitator_form_error: str = ""

    def set_show_add_facilitator(self, value: bool):
        self.show_add_facilitator = value
        if not value:
            self.new_facilitator_empid = ""
            self.new_facilitator_name = ""
            self.new_facilitator_email = ""
            self.new_facilitator_phone = ""
            self.new_facilitator_password = ""
            self.facilitator_form_error = ""

    def set_new_facilitator_empid(self, value: str):
        self.new_facilitator_empid = value

    def set_new_facilitator_name(self, value: str):
        self.new_facilitator_name = value

    def set_new_facilitator_email(self, value: str):
        self.new_facilitator_email = value

    def set_new_facilitator_phone(self, value: str):
        self.new_facilitator_phone = value

    def set_new_facilitator_password(self, value: str):
        self.new_facilitator_password = value

    def add_facilitator(self):
        if not all([
            self.new_facilitator_empid, self.new_facilitator_name,
            self.new_facilitator_email, self.new_facilitator_phone,
            self.new_facilitator_password,
        ]):
            self.facilitator_form_error = "Please fill in all fields."
            return
        if not re.match(FACILITATOR_ID_REGEX, self.new_facilitator_empid):
            self.facilitator_form_error = "Facilitator ID must be in the format F001–F999."
            return
        if not re.match(EMAIL_REGEX, self.new_facilitator_email):
            self.facilitator_form_error = "Enter a valid email address."
            return
        if not re.match(PHONE_REGEX, self.new_facilitator_phone):
            self.facilitator_form_error = "Phone number must be exactly 10 digits."
            return
        if len(self.new_facilitator_password) < 6:
            self.facilitator_form_error = "Password must be at least 6 characters."
            return
        if any(f["emp_id"] == self.new_facilitator_empid for f in self.facilitators):
            self.facilitator_form_error = "This Employee ID already exists."
            return

        new_f: Facilitator = {
            "emp_id": self.new_facilitator_empid,
            "name": self.new_facilitator_name,
            "email": self.new_facilitator_email,
            "phone": self.new_facilitator_phone,
            "password": self.new_facilitator_password,
        }
        self.facilitators.append(new_f)
        if not any(f["emp_id"] == new_f["emp_id"] for f in SHARED_FACILITATORS):
            SHARED_FACILITATORS.append(new_f)
        self.set_show_add_facilitator(False)

    # =========================================================
    # EDIT FACILITATOR (dialog/form)
    # =========================================================
    show_edit_facilitator: bool = False
    edit_facilitator_index: int = -1
    edit_facilitator_empid: str = ""
    edit_facilitator_name: str = ""
    edit_facilitator_email: str = ""
    edit_facilitator_phone: str = ""
    edit_facilitator_password: str = ""
    edit_facilitator_error: str = ""

    def open_edit_facilitator(self, index: int):
        f = self.facilitators[index]
        self.edit_facilitator_index = index
        self.edit_facilitator_empid = f["emp_id"]
        self.edit_facilitator_name = f["name"]
        self.edit_facilitator_email = f["email"]
        self.edit_facilitator_phone = f["phone"]
        self.edit_facilitator_password = f["password"]
        self.edit_facilitator_error = ""
        self.show_edit_facilitator = True

    def set_show_edit_facilitator(self, value: bool):
        self.show_edit_facilitator = value
        if not value:
            self.edit_facilitator_index = -1
            self.edit_facilitator_error = ""

    def set_edit_facilitator_empid(self, value: str):
        self.edit_facilitator_empid = value

    def set_edit_facilitator_name(self, value: str):
        self.edit_facilitator_name = value

    def set_edit_facilitator_email(self, value: str):
        self.edit_facilitator_email = value

    def set_edit_facilitator_phone(self, value: str):
        self.edit_facilitator_phone = value

    def set_edit_facilitator_password(self, value: str):
        self.edit_facilitator_password = value

    def save_edit_facilitator(self):
        if not all([
            self.edit_facilitator_empid, self.edit_facilitator_name,
            self.edit_facilitator_email, self.edit_facilitator_phone,
            self.edit_facilitator_password,
        ]):
            self.edit_facilitator_error = "Please fill in all fields."
            return
        if not re.match(FACILITATOR_ID_REGEX, self.edit_facilitator_empid):
            self.edit_facilitator_error = "Facilitator ID must be in the format F001–F999."
            return
        if not re.match(EMAIL_REGEX, self.edit_facilitator_email):
            self.edit_facilitator_error = "Enter a valid email address."
            return
        if not re.match(PHONE_REGEX, self.edit_facilitator_phone):
            self.edit_facilitator_error = "Phone number must be exactly 10 digits."
            return
        if len(self.edit_facilitator_password) < 6:
            self.edit_facilitator_error = "Password must be at least 6 characters."
            return
        for i, f in enumerate(self.facilitators):
            if i != self.edit_facilitator_index and f["emp_id"] == self.edit_facilitator_empid:
                self.edit_facilitator_error = "This Employee ID already exists."
                return

        self.facilitators[self.edit_facilitator_index] = {
            "emp_id": self.edit_facilitator_empid,
            "name": self.edit_facilitator_name,
            "email": self.edit_facilitator_email,
            "phone": self.edit_facilitator_phone,
            "password": self.edit_facilitator_password,
        }
        self.set_show_edit_facilitator(False)

    # =========================================================
    # DELETE FACILITATOR (confirm dialog)
    # =========================================================
    show_delete_facilitator: bool = False
    delete_facilitator_index: int = -1
    delete_facilitator_name: str = ""

    def open_delete_facilitator(self, index: int):
        self.delete_facilitator_index = index
        self.delete_facilitator_name = self.facilitators[index]["name"]
        self.show_delete_facilitator = True

    def set_show_delete_facilitator(self, value: bool):
        self.show_delete_facilitator = value
        if not value:
            self.delete_facilitator_index = -1
            self.delete_facilitator_name = ""

    def confirm_delete_facilitator(self):
        if 0 <= self.delete_facilitator_index < len(self.facilitators):
            del self.facilitators[self.delete_facilitator_index]
        self.set_show_delete_facilitator(False)

    # =========================================================
    # ADD CANDIDATE (dialog/form)
    # =========================================================
    show_add_candidate: bool = False
    new_candidate_id: str = ""
    new_candidate_name: str = ""
    new_candidate_email: str = ""
    new_candidate_password: str = ""
    candidate_form_error: str = ""

    def set_show_add_candidate(self, value: bool):
        self.show_add_candidate = value
        if not value:
            self.new_candidate_id = ""
            self.new_candidate_name = ""
            self.new_candidate_email = ""
            self.new_candidate_password = ""
            self.candidate_form_error = ""

    def set_new_candidate_id(self, value: str):
        self.new_candidate_id = value

    def set_new_candidate_name(self, value: str):
        self.new_candidate_name = value

    def set_new_candidate_email(self, value: str):
        self.new_candidate_email = value

    def set_new_candidate_password(self, value: str):
        self.new_candidate_password = value

    def add_candidate(self):
        if not all([
            self.new_candidate_id, self.new_candidate_name,
            self.new_candidate_email, self.new_candidate_password,
        ]):
            self.candidate_form_error = "Please fill in all fields."
            return
        if not re.match(EMAIL_REGEX, self.new_candidate_email):
            self.candidate_form_error = "Enter a valid email address."
            return
        if len(self.new_candidate_password) < 6:
            self.candidate_form_error = "Password must be at least 6 characters."
            return
        if any(c["emp_id"] == self.new_candidate_id for c in self.candidates):
            self.candidate_form_error = "This Candidate ID already exists."
            return

        new_c: Candidate = {
            "emp_id": self.new_candidate_id,
            "name": self.new_candidate_name,
            "email": self.new_candidate_email,
            "password": self.new_candidate_password,
        }
        self.candidates.append(new_c)
        if not any(c["emp_id"] == new_c["emp_id"] for c in SHARED_CANDIDATES):
            SHARED_CANDIDATES.append(new_c)
        self.set_show_add_candidate(False)
    # =========================================================
    # EDIT CANDIDATE (dialog/form)
    # =========================================================
    show_edit_candidate: bool = False
    edit_candidate_index: int = -1
    edit_candidate_id: str = ""
    edit_candidate_name: str = ""
    edit_candidate_email: str = ""
    edit_candidate_password: str = ""
    edit_candidate_error: str = ""

    def open_edit_candidate(self, index: int):
        c = self.candidates[index]
        self.edit_candidate_index = index
        self.edit_candidate_id = c["emp_id"]
        self.edit_candidate_name = c["name"]
        self.edit_candidate_email = c["email"]
        self.edit_candidate_password = c["password"]
        self.edit_candidate_error = ""
        self.show_edit_candidate = True

    def set_show_edit_candidate(self, value: bool):
        self.show_edit_candidate = value
        if not value:
            self.edit_candidate_index = -1
            self.edit_candidate_error = ""

    def set_edit_candidate_id(self, value: str):
        self.edit_candidate_id = value

    def set_edit_candidate_name(self, value: str):
        self.edit_candidate_name = value

    def set_edit_candidate_email(self, value: str):
        self.edit_candidate_email = value

    def set_edit_candidate_password(self, value: str):
        self.edit_candidate_password = value

    def save_edit_candidate(self):
        if not all([
            self.edit_candidate_id, self.edit_candidate_name,
            self.edit_candidate_email, self.edit_candidate_password,
        ]):
            self.edit_candidate_error = "Please fill in all fields."
            return
        if not re.match(EMAIL_REGEX, self.edit_candidate_email):
            self.edit_candidate_error = "Enter a valid email address."
            return
        if len(self.edit_candidate_password) < 6:
            self.edit_candidate_error = "Password must be at least 6 characters."
            return
        for i, c in enumerate(self.candidates):
            if i != self.edit_candidate_index and c["emp_id"] == self.edit_candidate_id:
                self.edit_candidate_error = "This Candidate ID already exists."
                return

        self.candidates[self.edit_candidate_index] = {
            "emp_id": self.edit_candidate_id,
            "name": self.edit_candidate_name,
            "email": self.edit_candidate_email,
            "password": self.edit_candidate_password,
        }
        self.set_show_edit_candidate(False)
    # =========================================================
    # DELETE CANDIDATE (confirm dialog)
    # =========================================================
    show_delete_candidate: bool = False
    delete_candidate_index: int = -1
    delete_candidate_name: str = ""

    def open_delete_candidate(self, index: int):
        self.delete_candidate_index = index
        self.delete_candidate_name = self.candidates[index]["name"]
        self.show_delete_candidate = True

    def set_show_delete_candidate(self, value: bool):
        self.show_delete_candidate = value
        if not value:
            self.delete_candidate_index = -1
            self.delete_candidate_name = ""

    def confirm_delete_candidate(self):
        if 0 <= self.delete_candidate_index < len(self.candidates):
            deleted_id = self.candidates[self.delete_candidate_index]["emp_id"]
            del self.candidates[self.delete_candidate_index]

            # Remove the deleted candidate from every assessment's
            # assigned_candidates list too (Assessment->Candidate is the
            # only remaining place candidates get assigned).
            for i, a in enumerate(self.assessments):
                if deleted_id in a["assigned_candidates"]:
                    updated_a = dict(a)
                    updated_a["assigned_candidates"] = [
                        cid for cid in a["assigned_candidates"] if cid != deleted_id
                    ]
                    self.assessments[i] = updated_a

        self.set_show_delete_candidate(False)

    # =========================================================
    # ASSESSMENTS — mock data
    # =========================================================
    assessments: list[Assessment] = [
        {
            "name": "Quality",
            # Multi-facilitator (primary)
            "facilitator_ids": ["F001", "F002"],
            "facilitator_names": ["Ravi Kumar", "Meena Iyer"],
            # Legacy aliases (first in list)
            "facilitator_id": "F001",
            "facilitator_name": "Ravi Kumar",
            "assigned_candidates": ["CAND-2031", "CAND-2054", "CAND-2061"],
            "status": "Scheduled",
            # Tests start empty — Facilitators add them via their workspace
            "tests": [],
            "final_test": "",
            "approval_status": "approved",
            "facilitator_approvals": {
                "F001": "approved",
                "F002": "approved",
            },
            "question_papers": {},
            "test_dates": {},
        }
    ]

    assessment_status_options: list[str] = ["Draft", "Scheduled", "Active", "Completed"]

    @rx.var
    def total_assessments(self) -> int:
        return len(self.assessments)

    @rx.var
    def total_approved_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "approved")

    @rx.var
    def total_pending_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "pending")

    @rx.var
    def total_declined_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "declined")

    # =========================================================
    # ADD ASSESSMENT (dialog/form)
    # =========================================================
    show_add_assessment: bool = False
    new_assessment_name: str = ""
    new_assessment_date: str = ""
    # Multi-select: list of selected facilitator IDs
    new_assessment_facilitator_ids: list[str] = []
    new_assessment_status: str = "Scheduled"
    new_assessment_candidate_ids: list[str] = []
    assessment_form_error: str = ""
    show_add_candidate_dropdown: bool = False
    # Search state — Add form
    add_facilitator_search: str = ""
    show_add_facilitator_dropdown: bool = False
    add_candidate_search: str = ""

    def set_show_add_assessment(self, value: bool):
        self.show_add_assessment = value
        if not value:
            self.new_assessment_name = ""
            self.new_assessment_date = ""
            self.new_assessment_facilitator_ids = []
            self.new_assessment_status = "Scheduled"
            self.new_assessment_candidate_ids = []
            self.assessment_form_error = ""
            self.show_add_candidate_dropdown = False
            self.add_facilitator_search = ""
            self.show_add_facilitator_dropdown = False
            self.add_candidate_search = ""

    def set_new_assessment_name(self, value: str):
        self.new_assessment_name = value

    def set_new_assessment_date(self, value: str):
        self.new_assessment_date = value

    def set_new_assessment_status(self, value: str):
        self.new_assessment_status = value

    # ---- Facilitator searchable dropdown — Add form ----
    def set_add_facilitator_search(self, value: str):
        self.add_facilitator_search = value

    def toggle_add_facilitator_dropdown(self):
        self.show_add_facilitator_dropdown = not self.show_add_facilitator_dropdown
        if self.show_add_facilitator_dropdown:
            self.add_facilitator_search = ""

    def toggle_add_facilitator(self, facilitator_id: str):
        """Toggle a facilitator's membership in the new-assessment selection list."""
        ids = list(self.new_assessment_facilitator_ids)
        if facilitator_id in ids:
            ids.remove(facilitator_id)
        else:
            ids.append(facilitator_id)
        self.new_assessment_facilitator_ids = ids

    # ---- Candidate multi-select search — Add form ----
    def set_add_candidate_search(self, value: str):
        self.add_candidate_search = value

    def toggle_add_candidate_dropdown(self):
        """Open/close the candidate multi-select panel in the Add Assessment form."""
        self.show_add_candidate_dropdown = not self.show_add_candidate_dropdown
        if not self.show_add_candidate_dropdown:
            self.add_candidate_search = ""

    def toggle_new_assessment_candidate(self, candidate_id: str):
        ids = list(self.new_assessment_candidate_ids)
        if candidate_id in ids:
            ids.remove(candidate_id)
        else:
            ids.append(candidate_id)
        self.new_assessment_candidate_ids = ids

    # ---- Computed filter vars — Add form ----
    @rx.var
    def filtered_add_facilitators(self) -> list[Facilitator]:
        q = self.add_facilitator_search.lower().strip()
        if not q:
            return self.facilitators
        return [f for f in self.facilitators if q in f["name"].lower() or q in f["emp_id"].lower()]

    @rx.var
    def selected_add_facilitator_names(self) -> list[str]:
        """Names of all selected facilitators (Add form)."""
        return [
            f["name"] for f in self.facilitators
            if f["emp_id"] in self.new_assessment_facilitator_ids
        ]

    @rx.var
    def selected_add_facilitators_label(self) -> str:
        """Display label for the Add form facilitator trigger row."""
        count = len(self.new_assessment_facilitator_ids)
        if count == 0:
            return ""
        if count == 1:
            names = [
                f["name"] for f in self.facilitators
                if f["emp_id"] in self.new_assessment_facilitator_ids
            ]
            return names[0] if names else ""
        return f"{count} facilitators selected"

    @rx.var
    def filtered_add_candidates(self) -> list[Candidate]:
        q = self.add_candidate_search.lower().strip()
        if not q:
            return self.candidates
        return [c for c in self.candidates if q in c["name"].lower() or q in c["emp_id"].lower()]

    def add_assessment(self):
        if not self.new_assessment_name or len(self.new_assessment_facilitator_ids) == 0:
            self.assessment_form_error = "Please fill in name and at least one facilitator."
            return

        selected_facilitators = [
            f for f in self.facilitators
            if f["emp_id"] in self.new_assessment_facilitator_ids
        ]
        if not selected_facilitators:
            self.assessment_form_error = "Selected facilitator(s) not found."
            return

        fac_ids = [f["emp_id"] for f in selected_facilitators]
        fac_names = [f["name"] for f in selected_facilitators]

        self.assessments.append({
            "name": self.new_assessment_name,
            "assessment_date": self.new_assessment_date,
            # Multi-facilitator
            "facilitator_ids": fac_ids,
            "facilitator_names": fac_names,
            # Legacy aliases
            "facilitator_id": fac_ids[0],
            "facilitator_name": fac_names[0],
            "assigned_candidates": list(self.new_assessment_candidate_ids),
            "status": self.new_assessment_status,
            "tests": [],
            "final_test": "",
            "approval_status": "pending",
            "test_dates": {},
        })
        self.set_show_add_assessment(False)

    # =========================================================
    # EDIT ASSESSMENT (dialog/form)
    # =========================================================
    show_edit_assessment: bool = False
    edit_assessment_index: int = -1
    edit_assessment_name: str = ""
    edit_assessment_date: str = ""
    # Multi-select: list of selected facilitator IDs
    edit_assessment_facilitator_ids: list[str] = []
    edit_assessment_status: str = ""
    edit_assessment_candidate_ids: list[str] = []
    edit_assessment_error: str = ""
    # Search state — Edit form
    edit_facilitator_search: str = ""
    show_edit_facilitator_dropdown: bool = False
    edit_candidate_search: str = ""

    def open_edit_assessment(self, index: int):
        a = self.assessments[index]
        self.edit_assessment_index = index
        self.edit_assessment_name = a["name"]
        self.edit_assessment_date = a.get("assessment_date", "")
        # Load existing multi-facilitator list; fall back to legacy single value
        existing_ids = a.get("facilitator_ids", [])
        if not existing_ids and a.get("facilitator_id"):
            existing_ids = [a["facilitator_id"]]
        self.edit_assessment_facilitator_ids = list(existing_ids)
        self.edit_assessment_status = a["status"]
        self.edit_assessment_candidate_ids = list(a["assigned_candidates"])
        self.edit_assessment_error = ""
        self.edit_facilitator_search = ""
        self.show_edit_facilitator_dropdown = False
        self.edit_candidate_search = ""
        self.show_edit_assessment = True

    def set_show_edit_assessment(self, value: bool):
        self.show_edit_assessment = value
        if not value:
            self.edit_assessment_index = -1
            self.edit_assessment_error = ""
            self.edit_facilitator_search = ""
            self.show_edit_facilitator_dropdown = False
            self.edit_candidate_search = ""

    def set_edit_assessment_name(self, value: str):
        self.edit_assessment_name = value

    def set_edit_assessment_date(self, value: str):
        self.edit_assessment_date = value

    def set_edit_assessment_status(self, value: str):
        self.edit_assessment_status = value

    # ---- Facilitator searchable dropdown — Edit form ----
    def set_edit_facilitator_search(self, value: str):
        self.edit_facilitator_search = value

    def toggle_edit_facilitator_dropdown(self):
        self.show_edit_facilitator_dropdown = not self.show_edit_facilitator_dropdown
        if self.show_edit_facilitator_dropdown:
            self.edit_facilitator_search = ""

    def toggle_edit_facilitator(self, facilitator_id: str):
        """Toggle a facilitator's membership in the edit-assessment selection list."""
        ids = list(self.edit_assessment_facilitator_ids)
        if facilitator_id in ids:
            ids.remove(facilitator_id)
        else:
            ids.append(facilitator_id)
        self.edit_assessment_facilitator_ids = ids

    # ---- Candidate search — Edit form ----
    def set_edit_candidate_search(self, value: str):
        self.edit_candidate_search = value

    def toggle_edit_assessment_candidate(self, candidate_id: str):
        ids = list(self.edit_assessment_candidate_ids)
        if candidate_id in ids:
            ids.remove(candidate_id)
        else:
            ids.append(candidate_id)
        self.edit_assessment_candidate_ids = ids

    # ---- Computed filter vars — Edit form ----
    @rx.var
    def filtered_edit_facilitators(self) -> list[Facilitator]:
        q = self.edit_facilitator_search.lower().strip()
        if not q:
            return self.facilitators
        return [f for f in self.facilitators if q in f["name"].lower() or q in f["emp_id"].lower()]

    @rx.var
    def selected_edit_facilitator_names(self) -> list[str]:
        """Names of all selected facilitators (Edit form)."""
        return [
            f["name"] for f in self.facilitators
            if f["emp_id"] in self.edit_assessment_facilitator_ids
        ]

    @rx.var
    def selected_edit_facilitators_label(self) -> str:
        """Display label for the Edit form facilitator trigger row."""
        count = len(self.edit_assessment_facilitator_ids)
        if count == 0:
            return ""
        if count == 1:
            names = [
                f["name"] for f in self.facilitators
                if f["emp_id"] in self.edit_assessment_facilitator_ids
            ]
            return names[0] if names else ""
        return f"{count} facilitators selected"

    @rx.var
    def filtered_edit_candidates(self) -> list[Candidate]:
        q = self.edit_candidate_search.lower().strip()
        if not q:
            return self.candidates
        return [c for c in self.candidates if q in c["name"].lower() or q in c["emp_id"].lower()]

    def save_edit_assessment(self):
        if not self.edit_assessment_name or len(self.edit_assessment_facilitator_ids) == 0:
            self.edit_assessment_error = "Please fill in name and at least one facilitator."
            return

        selected_facilitators = [
            f for f in self.facilitators
            if f["emp_id"] in self.edit_assessment_facilitator_ids
        ]
        if not selected_facilitators:
            self.edit_assessment_error = "Selected facilitator(s) not found."
            return

        fac_ids = [f["emp_id"] for f in selected_facilitators]
        fac_names = [f["name"] for f in selected_facilitators]

        existing_a = self.assessments[self.edit_assessment_index]
        existing_tests = existing_a.get("tests", [])
        existing_final_test = existing_a.get("final_test", "")
        existing_test_dates = existing_a.get("test_dates", {})
        existing_qps = existing_a.get("question_papers", {})

        self.assessments[self.edit_assessment_index] = {
            "name": self.edit_assessment_name,
            "assessment_date": self.edit_assessment_date,
            # Multi-facilitator
            "facilitator_ids": fac_ids,
            "facilitator_names": fac_names,
            # Legacy aliases
            "facilitator_id": fac_ids[0],
            "facilitator_name": fac_names[0],
            "assigned_candidates": list(self.edit_assessment_candidate_ids),
            "status": self.edit_assessment_status,
            "tests": existing_tests,
            "final_test": existing_final_test,
            "approval_status": "pending",
            "test_dates": existing_test_dates,
            "question_papers": existing_qps,
        }
        self.set_show_edit_assessment(False)

    # =========================================================
    # DELETE ASSESSMENT (confirm dialog)
    # =========================================================
    show_delete_assessment: bool = False
    delete_assessment_index: int = -1
    delete_assessment_name: str = ""

    def open_delete_assessment(self, index: int):
        self.delete_assessment_index = index
        self.delete_assessment_name = self.assessments[index]["name"]
        self.show_delete_assessment = True

    def set_show_delete_assessment(self, value: bool):
        self.show_delete_assessment = value
        if not value:
            self.delete_assessment_index = -1
            self.delete_assessment_name = ""

    def confirm_delete_assessment(self):
        if 0 <= self.delete_assessment_index < len(self.assessments):
            del self.assessments[self.delete_assessment_index]
        self.set_show_delete_assessment(False)

    # =========================================================
    # FEEDBACK FORM BUILDER (UI-only)
    # =========================================================
    show_feedback_type_dialog: bool = False
    feedback_assessment_index: int = -1
    feedback_assessment_name: str = ""

    # Facilitator form builder
    show_facilitator_feedback_builder: bool = False
    facilitator_form_title: str = ""
    facilitator_form_questions: list[dict] = []
    _facilitator_q_counter: int = 0
    facilitator_saved_forms: dict[str, dict] = {}

    # Candidate form builder
    show_candidate_feedback_builder: bool = False
    candidate_form_title: str = ""
    candidate_form_questions: list[dict] = []
    _candidate_q_counter: int = 0

    def open_feedback_dialog(self, index: int):
        self.feedback_assessment_index = index
        self.feedback_assessment_name = self.assessments[index]["name"]
        self.show_feedback_type_dialog = True

    def set_show_feedback_type_dialog(self, value: bool):
        self.show_feedback_type_dialog = value
        if not value:
            self.feedback_assessment_index = -1
            self.feedback_assessment_name = ""

    def close_feedback_type_dialog(self):
        self.show_feedback_type_dialog = False

    # ── Facilitator form ──────────────────────────────────────
    def open_facilitator_feedback_builder(self):
        self.show_feedback_type_dialog = False
        saved = self.facilitator_saved_forms.get(self.feedback_assessment_name)
        if saved:
            self.facilitator_form_title = saved.get("title", f"Facilitator Feedback Form - {self.feedback_assessment_name}")
            self.facilitator_form_questions = [dict(q) for q in saved.get("questions", [])]
            self._facilitator_q_counter = len(self.facilitator_form_questions)
        else:
            self.facilitator_form_title = f"Facilitator Feedback Form - {self.feedback_assessment_name}"
            self.facilitator_form_questions = []
            self._facilitator_q_counter = 0
        self.show_facilitator_feedback_builder = True

    def set_show_facilitator_feedback_builder(self, value: bool):
        self.show_facilitator_feedback_builder = value

    def close_facilitator_feedback_builder(self):
        self.show_facilitator_feedback_builder = False
        self.facilitator_form_title = ""
        self.facilitator_form_questions = []
        self._facilitator_q_counter = 0

    def set_facilitator_form_title(self, value: str):
        self.facilitator_form_title = value

    def add_facilitator_question(self):
        self._facilitator_q_counter += 1
        new_q = {
            "id": f"fq_{self._facilitator_q_counter}",
            "text": "",
            "required": True,
        }
        self.facilitator_form_questions = self.facilitator_form_questions + [new_q]

    def set_facilitator_question_text(self, qid: str, value: str):
        qs = [dict(q) for q in self.facilitator_form_questions]
        for q in qs:
            if q["id"] == qid:
                q["text"] = value
                break
        self.facilitator_form_questions = qs

    def toggle_facilitator_question_required(self, qid: str):
        qs = [dict(q) for q in self.facilitator_form_questions]
        for q in qs:
            if q["id"] == qid:
                q["required"] = not q["required"]
                break
        self.facilitator_form_questions = qs

    def delete_facilitator_question(self, qid: str):
        self.facilitator_form_questions = [
            q for q in self.facilitator_form_questions if q["id"] != qid
        ]

    def submit_facilitator_feedback_form(self):
        """Save facilitator feedback questions per assessment and close builder."""
        asmn = self.feedback_assessment_name
        title = self.facilitator_form_title or f"Facilitator Feedback Form - {asmn}"
        qs = [dict(q) for q in self.facilitator_form_questions]
        saved = dict(self.facilitator_saved_forms)
        saved[asmn] = {
            "title": title,
            "questions": qs,
        }
        self.facilitator_saved_forms = saved
        self.show_facilitator_feedback_builder = False
        return rx.toast.success("Facilitator Feedback Form created successfully.")

    # ── Candidate form ────────────────────────────────────────
    def open_candidate_feedback_builder(self):
        self.show_feedback_type_dialog = False
        self.candidate_form_title = f"Candidate Feedback Form - {self.feedback_assessment_name}"
        self.candidate_form_questions = []
        self._candidate_q_counter = 0
        self.show_candidate_feedback_builder = True

    def set_show_candidate_feedback_builder(self, value: bool):
        self.show_candidate_feedback_builder = value

    def close_candidate_feedback_builder(self):
        self.show_candidate_feedback_builder = False
        self.candidate_form_title = ""
        self.candidate_form_questions = []
        self._candidate_q_counter = 0

    def set_candidate_form_title(self, value: str):
        self.candidate_form_title = value

    def add_candidate_question(self):
        self._candidate_q_counter += 1
        new_q = {
            "id": f"cq_{self._candidate_q_counter}",
            "text": "",
            "required": True,
        }
        self.candidate_form_questions = self.candidate_form_questions + [new_q]

    def set_candidate_question_text(self, qid: str, value: str):
        qs = [dict(q) for q in self.candidate_form_questions]
        for q in qs:
            if q["id"] == qid:
                q["text"] = value
                break
        self.candidate_form_questions = qs

    def toggle_candidate_question_required(self, qid: str):
        qs = [dict(q) for q in self.candidate_form_questions]
        for q in qs:
            if q["id"] == qid:
                q["required"] = not q["required"]
                break
        self.candidate_form_questions = qs

    def delete_candidate_question(self, qid: str):
        self.candidate_form_questions = [
            q for q in self.candidate_form_questions if q["id"] != qid
        ]

    def submit_candidate_feedback_form(self):
        """UI-only: just close the builder."""
        self.close_candidate_feedback_builder()

    # =========================================================
    # ASSESSMENT TESTS (Type of Test Dialog)
    # =========================================================
    show_assessment_tests_dialog: bool = False
    selected_tests_assessment_index: int = -1

    def open_assessment_tests(self, index: int):
        """Open the Type of Test modal for the clicked assessment."""
        self.selected_tests_assessment_index = index
        if 0 <= index < len(self.assessments):
            a = dict(self.assessments[index])
            if "tests" not in a:
                a["tests"] = []
            if "final_test" not in a or not a["final_test"]:
                a["final_test"] = "Summative Test"
            self.assessments[index] = a
        self.show_assessment_tests_dialog = True

    def set_show_assessment_tests_dialog(self, value: bool):
        self.show_assessment_tests_dialog = value
        if not value:
            self.selected_tests_assessment_index = -1

    @rx.var
    def current_tests_assessment_name(self) -> str:
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            return self.assessments[self.selected_tests_assessment_index]["name"]
        return ""

    @rx.var
    def current_assessment_tests(self) -> list[str]:
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            return self.assessments[self.selected_tests_assessment_index].get("tests", [])
        return []

    @rx.var
    def current_assessment_tests_with_dates(self) -> list[dict]:
        """Returns list of formative test dicts with name and date for the open modal."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = self.assessments[self.selected_tests_assessment_index]
            tests = a.get("tests", [])
            dates = a.get("test_dates", {})
            items = []
            for t in tests:
                d = dates.get(t, "")
                items.append({"name": t, "date": d})
            return items
        return []

    @rx.var
    def current_assessment_final_test(self) -> str:
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            return self.assessments[self.selected_tests_assessment_index].get("final_test", "Summative Test")
        return "Summative Test"

    @rx.var
    def current_assessment_final_test_date(self) -> str:
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = self.assessments[self.selected_tests_assessment_index]
            final_name = a.get("final_test", "Summative Test")
            return a.get("test_dates", {}).get(final_name, "") or ""
        return ""

    @rx.var
    def current_test_dates(self) -> dict:
        """Returns the test_dates dict for the currently open Type-of-Test dialog."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            return self.assessments[self.selected_tests_assessment_index].get("test_dates", {})
        return {}

    def set_test_date(self, test_name: str, value: str):
        """Update the per-test conducted date."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = dict(self.assessments[self.selected_tests_assessment_index])
            dates = dict(a.get("test_dates", {}))
            dates[test_name] = value
            a["test_dates"] = dates
            self.assessments[self.selected_tests_assessment_index] = a

    def add_test_to_selected_assessment(self):
        """Automatically increments formative test count: Formative 1 -> Formative 2 -> Formative N..."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = dict(self.assessments[self.selected_tests_assessment_index])
            current_list = list(a.get("tests", []))
            next_num = len(current_list) + 1
            new_test_name = f"Formative {next_num}"
            current_list.append(new_test_name)
            a["tests"] = current_list
            # Initialise empty date for the new test
            dates = dict(a.get("test_dates", {}))
            dates[new_test_name] = ""
            a["test_dates"] = dates
            self.assessments[self.selected_tests_assessment_index] = a

    def remove_test_from_selected_assessment(self, test_name: str):
        """Removes a formative test (can delete down to 0 formative tests)."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = dict(self.assessments[self.selected_tests_assessment_index])
            current_list = list(a.get("tests", []))
            if test_name in current_list:
                current_list.remove(test_name)
                # Re-number remaining formative tests: Formative 1, Formative 2, ...
                renumbered = [f"Formative {i + 1}" for i in range(len(current_list))]
                a["tests"] = renumbered
                # Rebuild test_dates with new names
                old_dates = dict(a.get("test_dates", {}))
                final_test = a.get("final_test", "Summative Test")
                new_dates = {final_test: old_dates.get(final_test, "")}
                for name in renumbered:
                    new_dates[name] = old_dates.get(name, "")
                a["test_dates"] = new_dates
                # Clean up question paper for this test if present
                assessment_name = a["name"]
                test_id = f"{assessment_name}__{test_name}"
                qps = dict(self.test_question_papers)
                if test_id in qps:
                    del qps[test_id]
                    self.test_question_papers = qps
                old_qps = dict(a.get("question_papers", {}))
                if test_name in old_qps:
                    del old_qps[test_name]
                    a["question_papers"] = old_qps

                self.assessments[self.selected_tests_assessment_index] = a

    # =========================================================
    # TEST DETAILS / UPDATES (When Admin clicks a test badge)
    # =========================================================
    show_test_details_dialog: bool = False
    viewing_test_assessment_index: int = -1
    viewing_test_name: str = ""

    def open_test_details(self, assessment_index: int, test_name: str):
        """Open the Test updates/details modal showing facilitator and candidates."""
        self.viewing_test_assessment_index = assessment_index
        self.viewing_test_name = test_name
        self.show_test_details_dialog = True

    def set_show_test_details_dialog(self, value: bool):
        self.show_test_details_dialog = value
        if not value:
            self.viewing_test_assessment_index = -1
            self.viewing_test_name = ""

    @rx.var
    def viewing_test_assessment_name(self) -> str:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            return self.assessments[self.viewing_test_assessment_index]["name"]
        return ""

    @rx.var
    def viewing_test_date(self) -> str:
        """Returns the per-test conducted date for the currently viewed test."""
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            a = self.assessments[self.viewing_test_assessment_index]
            test_dates = a.get("test_dates", {})
            t_name = self.viewing_test_name
            return test_dates.get(t_name, "")
        return ""

    @rx.var
    def viewing_test_facilitator_name(self) -> str:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            return self.assessments[self.viewing_test_assessment_index]["facilitator_name"]
        return ""

    @rx.var
    def viewing_test_facilitator_id(self) -> str:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            return self.assessments[self.viewing_test_assessment_index]["facilitator_id"]
        return ""

    @rx.var
    def viewing_test_facilitator_email(self) -> str:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            fac_id = self.assessments[self.viewing_test_assessment_index]["facilitator_id"]
            match = next((f for f in self.facilitators if f["emp_id"] == fac_id), None)
            return match["email"] if match else ""
        return ""

    @rx.var
    def viewing_test_facilitators_list(self) -> list[Facilitator]:
        """Returns list of facilitator dicts for all facilitators assigned to the viewed assessment."""
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            a = self.assessments[self.viewing_test_assessment_index]
            fac_ids = a.get("facilitator_ids", [])
            if not fac_ids and a.get("facilitator_id"):
                fac_ids = [a["facilitator_id"]]
            result = []
            for fid in fac_ids:
                match = next((f for f in self.facilitators if f["emp_id"] == fid), None)
                if match:
                    result.append(dict(match))
                else:
                    result.append({
                        "name": a.get("facilitator_name", "Facilitator"),
                        "emp_id": fid,
                        "email": f"{fid.lower()}@tvsmotor.com",
                        "phone": "",
                        "password": "",
                    })
            return result
        return []

    @rx.var
    def viewing_test_candidates_list(self) -> list[Candidate]:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            c_ids = self.assessments[self.viewing_test_assessment_index]["assigned_candidates"]
            return [c for c in self.candidates if c["emp_id"] in c_ids]
        return []

    # Test-wise Question Papers shared across Admin and Facilitator
    # Key: unique test ID (e.g. "Quality__Formative 1")
    test_question_papers: dict[str, str] = {
        "Quality__Formative 1": "Quality_Technical_Stage1.xlsx",
    }

    @rx.var
    def viewing_test_id(self) -> str:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            return f"{self.assessments[self.viewing_test_assessment_index]['name']}__{self.viewing_test_name}"
        return ""

    @rx.var
    def viewing_test_qp_filename(self) -> str:
        return self.test_question_papers.get(self.viewing_test_id, "")

    @rx.var
    def viewing_test_has_qp(self) -> bool:
        return bool(self.viewing_test_qp_filename)

    @rx.var
    def viewing_test_is_final(self) -> bool:
        return self.viewing_test_name.lower() == "summative test"


# ─────────────────────────────────────────────────────────────────────────────
# Admin Assessment Reports State
# Consumes Overall Assessment Reports generated from Facilitator assessment completion.
# ─────────────────────────────────────────────────────────────────────────────

class AdminReportsState(rx.State):
    """State for the Admin Reports page — consumes Overall Assessment Reports generated by Facilitators upon assessment completion."""

    # Consumed overall assessment reports from the Facilitator assessment/report flow.
    # Empty by default — no hard-coded mock dataset.
    submitted_reports: list[dict] = []

    # Search filter
    search_query: str = ""

    # Selected report for the right-hand preview panel
    selected_report_id: str = ""

    # Which report is currently being viewed in the detail modal
    show_report_detail: bool = False
    viewed_report_id: str = ""
    is_full_view: bool = False

    # Active analytics tab in the report detail view
    report_detail_tab: str = "overall"  # "overall"|"co"|"lo"|"knowledge_type"|"domain"|"rbt_level"

    def set_search_query(self, query: str):
        self.search_query = query

    def select_report(self, report_id: str):
        self.selected_report_id = report_id

    def open_report(self, report_id: str):
        self.viewed_report_id = report_id
        self.selected_report_id = report_id
        self.report_detail_tab = "overall"
        self.is_full_view = False
        self.show_report_detail = True

    def open_selected_report(self):
        if self.selected_report_id:
            self.open_report(self.selected_report_id)

    def toggle_full_view(self):
        self.is_full_view = not self.is_full_view

    def close_report(self):
        self.show_report_detail = False
        self.is_full_view = False

    def set_show_report_detail(self, value: bool):
        self.show_report_detail = value
        if not value:
            self.is_full_view = False

    def set_report_detail_tab(self, tab: str):
        self.report_detail_tab = tab

    def consume_facilitator_overall_report(self, report_data: dict):
        """Consume an Overall Assessment Report generated upon completion by a facilitator.
        Each report represents ONE completed assessment with test-wise, candidate-wise, score,
        CO, LO, Knowledge Type, Domain, and RBT details retained from the facilitator-generated report.
        """
        if not report_data or not report_data.get("report_id"):
            return
        # Deduplicate / update report
        existing = [r for r in self.submitted_reports if r.get("report_id") != report_data.get("report_id")]
        existing.insert(0, report_data)
        self.submitted_reports = existing
        if not self.selected_report_id:
            self.selected_report_id = report_data.get("report_id", "")

    @rx.var
    def current_report(self) -> dict:
        for r in self.submitted_reports:
            if r["report_id"] == self.viewed_report_id:
                return r
        return self.submitted_reports[0] if self.submitted_reports else {
            "report_id": "",
            "assessment_name": "",
            "facilitator_name": "",
            "facilitator_id": "",
            "assessment_date": "",
            "submitted_date": "",
            "submitted_time": "",
            "candidate_count": 0,
            "overall_score": 0,
            "final_test_score": 0,
            "passing_rate": "0%",
            "passing_count": "0 Candidates",
            "insight_diff": 0,
            "insight_start": "",
            "insight_end": "",
            "test_scores": [],
            "candidates": [],
            "co": [],
            "lo": [],
            "knowledge_type": [],
            "domain": [],
            "rbt_level": [],
        }

    @rx.var
    def selected_report_preview(self) -> dict:
        for r in self.submitted_reports:
            if r["report_id"] == self.selected_report_id:
                return r
        return self.submitted_reports[0] if self.submitted_reports else {}

    @rx.var
    def filtered_reports(self) -> list[dict]:
        q = self.search_query.strip().lower()
        res = []
        idx = 1
        for r in self.submitted_reports:
            if not q or q in r.get("assessment_name", "").lower() or q in r.get("facilitator_name", "").lower():
                item = dict(r)
                item["index_num"] = str(idx)
                res.append(item)
                idx += 1
        return res

    @rx.var
    def total_reports_count(self) -> str:
        return str(len(self.submitted_reports))

    @rx.var
    def total_candidates_count(self) -> str:
        return str(sum(r.get("candidate_count", 0) for r in self.submitted_reports))

    @rx.var
    def average_score_str(self) -> str:
        if not self.submitted_reports:
            return "0%"
        avg = sum(r.get("overall_score", 0) for r in self.submitted_reports) / len(self.submitted_reports)
        return f"{round(avg)}%"

    @rx.var
    def latest_report_date(self) -> str:
        if self.submitted_reports:
            return self.submitted_reports[0].get("submitted_date", "—")
        return "—"

    @rx.var
    def showing_text(self) -> str:
        total = len(self.submitted_reports)
        filtered = len(self.filtered_reports)
        if total == 0:
            return "Showing 0 reports"
        if filtered == 0:
            return f"Showing 0 of {total} reports"
        return f"Showing 1-{filtered} of {total} reports"

    @rx.var
    def preview_assessment_name(self) -> str:
        return self.selected_report_preview.get("assessment_name", "—")

    @rx.var
    def preview_report_id(self) -> str:
        return self.selected_report_preview.get("report_id", "—")

    @rx.var
    def preview_facilitator_name(self) -> str:
        return self.selected_report_preview.get("facilitator_name", "—")

    @rx.var
    def preview_report_date_time(self) -> str:
        date = self.selected_report_preview.get("submitted_date", "")
        time = self.selected_report_preview.get("submitted_time", "")
        if date and time:
            return f"{date}, {time}"
        return date or "—"

    @rx.var
    def preview_candidate_count(self) -> str:
        if not self.selected_report_preview or "candidate_count" not in self.selected_report_preview:
            return "—"
        return str(self.selected_report_preview.get("candidate_count", 0))

    @rx.var
    def preview_score_str(self) -> str:
        if not self.selected_report_preview or "overall_score" not in self.selected_report_preview:
            return "—"
        score = self.selected_report_preview.get("overall_score", 0)
        return f"{score}%"

    @rx.var
    def report_assessment_name(self) -> str:
        return self.current_report.get("assessment_name", "—")

    @rx.var
    def report_facilitator_name(self) -> str:
        return self.current_report.get("facilitator_name", "—")

    @rx.var
    def report_facilitator_id(self) -> str:
        return self.current_report.get("facilitator_id", "—")

    @rx.var
    def report_assessment_date(self) -> str:
        return self.current_report.get("assessment_date", "—")

    @rx.var
    def report_submitted_date(self) -> str:
        return self.current_report.get("submitted_date", "—")

    @rx.var
    def report_submitted_time(self) -> str:
        return self.current_report.get("submitted_time", "")

    @rx.var
    def report_candidate_count_str(self) -> str:
        cnt = self.current_report.get("candidate_count", 0)
        return str(cnt)

    @rx.var
    def report_overall_score_int(self) -> int:
        return int(self.current_report.get("overall_score", 0))

    @rx.var
    def report_overall_score_str(self) -> str:
        return f"{self.report_overall_score_int}%"

    @rx.var
    def report_passed_count_str(self) -> str:
        cands = self.report_candidate_table_rows
        if cands:
            passed = sum(1 for c in cands if c.get("status") == "Passed")
            return str(passed)
        rate_str = self.current_report.get("passing_count", "")
        if "of" in rate_str:
            parts = rate_str.split("of")
            return parts[0].strip()
        return "0"

    @rx.var
    def report_failed_count_str(self) -> str:
        cands = self.report_candidate_table_rows
        if cands:
            failed = sum(1 for c in cands if c.get("status") == "Failed")
            return str(failed)
        return "0"

    @rx.var
    def report_pending_count_str(self) -> str:
        cands = self.report_candidate_table_rows
        if cands:
            pending = sum(1 for c in cands if c.get("status") == "Pending")
            return str(pending)
        return "0"

    @rx.var
    def report_pass_rate_str(self) -> str:
        rate = self.current_report.get("passing_rate", "")
        if rate:
            return rate
        total = int(self.current_report.get("candidate_count", 0))
        passed = int(self.report_passed_count_str) if self.report_passed_count_str.isdigit() else 0
        if total > 0:
            return f"{round(passed / total * 100)}%"
        return "0%"

    @rx.var
    def report_candidates(self) -> list[dict]:
        return self.current_report.get("candidates", [])

    @rx.var
    def report_test_scores(self) -> list[dict]:
        return self.current_report.get("test_scores", [])

    @rx.var
    def report_test_wise_rows(self) -> list[dict]:
        tests = self.current_report.get("test_scores", [])
        asmn_date = (self.current_report.get("assessment_date", "") or "").strip()
        sub_date = (self.current_report.get("submitted_date", "") or "").strip()
        cand_count = self.current_report.get("candidate_count", 0)
        res = []
        for t in tests:
            t_name = t.get("name", "Test")
            is_final = t.get("is_final", False) or t.get("type") == "Summative" or "summative" in t_name.lower()
            avg = t.get("avg_score", 0)
            avg_str = t.get("avg_score_str", f"{int(avg)}%" if avg == int(avg) else f"{avg}%")
            weight = t.get("weightage", 0)
            # Use the stored per-test date; fall back to assessment date, submitted date, or today
            t_date = (t.get("date", "") or "").strip()
            if not t_date or t_date == "—":
                t_date = asmn_date
            if not t_date or t_date == "—":
                t_date = sub_date
            if not t_date or t_date == "—":
                from datetime import datetime
                t_date = datetime.now().strftime("%d %b %Y")
            evaluated = t.get("evaluated", 0)
            res.append({
                "name": t_name,
                "type": "Summative" if is_final else "Formative",
                "badge_scheme": "purple" if is_final else "blue",
                "date": t_date,
                "weightage": f"{weight}%" if isinstance(weight, (int, float)) else str(weight),
                "avg_score": avg_str,
                "avg_val": int(avg),
                "pass_pct": avg_str,
                "evaluated": f"{evaluated} / {cand_count}",
                "status": "Ready" if evaluated > 0 else "Pending",
            })
        return res

    @rx.var
    def report_candidate_table_rows(self) -> list[dict]:
        cands = self.current_report.get("candidates", [])
        tests = self.current_report.get("test_scores", [])
        test_names = [t.get("name", f"Test {i+1}") for i, t in enumerate(tests)]
        res = []
        for i, c in enumerate(cands, 1):
            raw_scores = c.get("scores", [])
            badges = []
            has_unevaluated = False
            has_any_score = False

            if isinstance(raw_scores, list):
                for idx, s in enumerate(raw_scores):
                    t_lbl = test_names[idx] if idx < len(test_names) else f"Test {idx+1}"
                    s_str = str(s).strip()
                    if s_str in ("—", "Pending", "", "None"):
                        has_unevaluated = True
                    else:
                        has_any_score = True
                    badges.append({"label": t_lbl, "score": s_str})
            else:
                s_str = str(raw_scores).strip()
                if s_str in ("—", "Pending", "", "None"):
                    has_unevaluated = True
                else:
                    has_any_score = True
                badges.append({"label": "Score", "score": s_str})

            scores_summary = "  •  ".join([f"{b['label']}: {b['score']}" for b in badges]) if badges else "—"

            ov_raw = str(c.get("overall_score", "0")).replace("%", "").strip()
            try:
                ov_val = float(ov_raw)
            except ValueError:
                ov_val = 0.0

            stored_status = str(c.get("status", "")).strip()

            # A candidate is Pending (unevaluated) if:
            # - They have unevaluated tests ("—" or "Pending" in test scores)
            # - No scores were evaluated
            # - Stored status is explicitly "Pending"
            # - Stored overall score is "—"
            # - Or overall score is 0% and stored status is "Failed" while test was never scored
            if has_unevaluated or not has_any_score or stored_status == "Pending" or str(c.get("overall_score", "")).strip() == "—" or (ov_val == 0.0 and stored_status == "Failed" and not has_any_score):
                status = "Pending"
                overall_score_str = "—"
                band = "—"
                band_color = "gray"
                ov_val = 0.0
            else:
                status = stored_status if stored_status in ("Passed", "Failed") else ("Passed" if ov_val >= 50 else "Failed")
                overall_score_str = str(c.get("overall_score", "—"))
                if ov_val >= 80:
                    band = "Distinction"
                    band_color = "green"
                elif ov_val >= 65:
                    band = "Proficient"
                    band_color = "indigo"
                elif ov_val >= 50:
                    band = "Satisfactory"
                    band_color = "amber"
                else:
                    band = "Needs Improvement"
                    band_color = "red"

            res.append({
                "idx": str(c.get("idx", i)),
                "cand_id": c.get("cand_id", c.get("emp_id", f"C{i:03d}")),
                "cand_name": c.get("cand_name", c.get("name", f"Candidate {i}")),
                "test_badges": badges,
                "scores_summary": scores_summary,
                "overall_score": overall_score_str,
                "overall_val": int(ov_val),
                "performance_band": band,
                "band_color": band_color,
                "status": status,
            })
        return res

    @rx.var
    def report_remarks_rows(self) -> list[dict]:
        cands = self.report_candidate_table_rows
        if not cands:
            return []
        res = []
        for c in cands:
            c_name = c.get("cand_name", c.get("name", "Candidate"))
            c_id = c.get("cand_id", c.get("emp_id", ""))
            status = c.get("status", "Pending")
            disp = f"{c_name} ({c_id})" if c_id else c_name
            if status == "Pending":
                rmk = "Evaluation pending — not all tests have been scored for this candidate."
            elif status == "Passed":
                rmk = "Demonstrated solid overall proficiency and fulfilled all assessment test requirements."
            else:
                rmk = "Requires targeted remediation in core competency modules to meet the required passing standard."
            res.append({
                "candidate": disp,
                "remarks": rmk,
            })
        return res

    @rx.var
    def report_co_scores(self) -> list[dict]:
        return self.current_report.get("co", [])

    @rx.var
    def report_lo_scores(self) -> list[dict]:
        return self.current_report.get("lo", [])

    @rx.var
    def report_knowledge_scores(self) -> list[dict]:
        return self.current_report.get("knowledge_type", [])

    @rx.var
    def report_domain_scores(self) -> list[dict]:
        return self.current_report.get("domain", [])

    @rx.var
    def report_rbt_scores(self) -> list[dict]:
        return self.current_report.get("rbt_level", [])

    @rx.var
    def report_active_dimension_items(self) -> list[dict]:
        tab = self.report_detail_tab
        r = self.current_report
        score = self.report_overall_score_int or 75
        if tab == "co":
            items = r.get("co", [])
            if not items:
                items = [
                    {"name": "CO1 - Foundational Principles & Core Concepts", "score": min(100, score + 4)},
                    {"name": "CO2 - Practical Execution & Standard Procedures", "score": max(30, score - 2)},
                    {"name": "CO3 - Quality Verification & Compliance Standards", "score": min(100, score + 1)},
                    {"name": "CO4 - Problem Diagnosis & Corrective Actions", "score": max(30, score - 5)},
                ]
            return items
        elif tab == "lo":
            items = r.get("lo", [])
            if not items:
                items = [
                    {"name": "LO1 - Identify Key Concepts & Regulatory Norms", "score": min(100, score + 6)},
                    {"name": "LO2 - Execute Operational Protocols Correctly", "score": max(30, score - 1)},
                    {"name": "LO3 - Analyze Fault Patterns & Performance Data", "score": max(30, score - 4)},
                    {"name": "LO4 - Formulate Improvement & Mitigation Plans", "score": min(100, score - 2)},
                ]
            return items
        elif tab == "knowledge_type":
            items = r.get("knowledge_type", [])
            if not items:
                items = [
                    {"name": "Factual Knowledge", "score": min(100, score + 8)},
                    {"name": "Conceptual Knowledge", "score": min(100, score + 2)},
                    {"name": "Procedural Knowledge", "score": max(30, score - 3)},
                    {"name": "Metacognitive Knowledge", "score": max(30, score - 6)},
                ]
            return items
        elif tab == "domain":
            items = r.get("domain", [])
            if not items:
                items = [
                    {"name": "Cognitive Domain", "score": min(100, score + 3)},
                    {"name": "Psychomotor Domain", "score": max(30, score - 2)},
                    {"name": "Affective Domain", "score": min(100, score + 5)},
                ]
            return items
        elif tab == "rbt_level":
            items = r.get("rbt_level", [])
            if not items:
                items = [
                    {"name": "Remember (L1)", "score": min(100, score + 10)},
                    {"name": "Understand (L2)", "score": min(100, score + 5)},
                    {"name": "Apply (L3)", "score": score},
                    {"name": "Analyze (L4)", "score": max(30, score - 4)},
                    {"name": "Evaluate (L5)", "score": max(30, score - 8)},
                    {"name": "Create (L6)", "score": max(30, score - 12)},
                ]
            return items
        return r.get("test_scores", [])

    @rx.var
    def report_insights_summary(self) -> dict:
        score = self.report_overall_score_int
        asmn = self.report_assessment_name
        p_rate = self.report_pass_rate_str
        cand_cnt = self.report_candidate_count_str

        if score >= 80:
            exec_summary = f"The cohort demonstrated outstanding competency in '{asmn}', achieving an overall average of {score}% with a {p_rate} pass rate across {cand_cnt} candidate(s)."
            strengths = "Strong conceptual grasp, disciplined procedural adherence, and robust evaluation consistency across formative and summative tests."
            focus_areas = "Introduce advanced troubleshooting drills, multi-variable fault isolation, and autonomous optimization tasks."
            recommendation = "Continue with current competency-based training framework and introduce real-world case simulations to further enhance mastery."
        elif score >= 60:
            exec_summary = f"The cohort achieved satisfactory performance in '{asmn}', scoring an overall average of {score}% with a {p_rate} pass rate across {cand_cnt} candidate(s)."
            strengths = "Good foundational knowledge and steady progression across core test benchmarks."
            focus_areas = "Procedural precision, complex edge-case resolution, and test-time execution efficiency."
            recommendation = "Schedule targeted reinforcement sessions focusing on weaker learning outcomes and provide hands-on practice labs."
        else:
            exec_summary = f"The cohort scored an overall average of {score}% in '{asmn}', with a {p_rate} pass rate across {cand_cnt} candidate(s)."
            strengths = "Active participation and baseline knowledge demonstrated across initial test items."
            focus_areas = "Significant remediation required in procedural execution, analytical thinking, and core competency mastery."
            recommendation = "Implement mandatory instructor-led remediation workshops followed by structured reassessment."

        return {
            "exec_summary": exec_summary,
            "strengths": strengths,
            "focus_areas": focus_areas,
            "recommendation": recommendation,
        }

    def mock_export_report(self):
        return rx.toast.info("Report exported as PDF (Mock)!")


# ─────────────────────────────────────────────────────────────
# Admin Feedback State
# ─────────────────────────────────────────────────────────────

class AdminFeedbackState(rx.State):
    """State for the Admin Feedback Management page — manages Candidate and Facilitator feedback."""

    active_tab: str = "candidate"  # "candidate" | "facilitator"

    # Filters
    filter_assessment: str = "All Assessments"
    filter_test: str = "All Tests"
    search_query: str = ""
    filter_rating: str = "All Ratings"
    filter_date_range: str = ""

    # Selected feedback item for the right-hand inspection details panel
    selected_entry: dict = {
        "id": "1",
        "key": "",
        "candidate_name": "",
        "candidate_id": "",
        "initial": "C",
        "assessment": "",
        "test": "",
        "rating": 0,
        "rating_str": "—",
        "star1": False,
        "star2": False,
        "star3": False,
        "star4": False,
        "star5": False,
        "feedback": "",
        "preview": "",
        "submitted_on": "",
        "date_line": "",
        "time_line": "",
        "tags": [],
        "type": "candidate",
        "facilitator": "",
    }
    show_details_panel: bool = True

    # Pagination
    current_page: int = 1
    items_per_page: int = 8

    # In-memory storage cache loaded from disk
    raw_candidate_feedbacks: dict = {}
    raw_facilitator_feedbacks: dict = {}

    @staticmethod
    def _get_data_dir() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def _load_data_from_disk(self):
        c_path = self._get_data_dir() / "candidate_feedbacks.json"
        if c_path.exists():
            try:
                with open(c_path, "r", encoding="utf-8") as f:
                    self.raw_candidate_feedbacks = json.load(f)
            except Exception:
                self.raw_candidate_feedbacks = {}
        else:
            self.raw_candidate_feedbacks = {}

        f_path = self._get_data_dir() / "facilitator_feedbacks.json"
        if f_path.exists():
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    self.raw_facilitator_feedbacks = json.load(f)
            except Exception:
                self.raw_facilitator_feedbacks = {}
        else:
            self.raw_facilitator_feedbacks = {}

    def on_load(self):
        """Sync latest feedback data from disk on page load."""
        self._load_data_from_disk()
        entries = self.filtered_entries
        if entries:
            self.selected_entry = entries[0]
            self.show_details_panel = True

    @rx.var
    def candidate_entries(self) -> list[dict]:
        entries: list[dict] = []
        i = 1
        for key, item in self.raw_candidate_feedbacks.items():
            c_name = item.get("candidate_name") or "Candidate"
            c_id = item.get("candidate_id") or "CAND-2031"
            asmn = item.get("assessment") or "Quality"
            test_name = item.get("test") or "Formative 1"
            rating = int(item.get("rating") or 0)
            fb = (item.get("feedback") or "").strip()
            preview = f'"{fb[:42]}..."' if len(fb) > 42 else (f'"{fb}"' if fb else "—")
            sub_on = item.get("submitted_at") or "14 Sep 2026 11:26 PM"

            date_line = sub_on
            time_line = ""
            if " " in sub_on:
                parts = sub_on.split(" ")
                date_line = " ".join(parts[:3]) if len(parts) >= 3 else parts[0]
                time_line = " ".join(parts[3:]) if len(parts) >= 3 else parts[-1]

            entries.append({
                "id": str(i),
                "key": key,
                "candidate_name": c_name,
                "candidate_id": c_id,
                "initial": c_name[0].upper() if c_name else "C",
                "assessment": asmn,
                "test": test_name,
                "rating": rating,
                "rating_str": f"{rating}/5",
                "star1": rating >= 1,
                "star2": rating >= 2,
                "star3": rating >= 3,
                "star4": rating >= 4,
                "star5": rating >= 5,
                "feedback": fb if fb else "No feedback text provided.",
                "preview": preview,
                "submitted_on": sub_on,
                "date_line": date_line,
                "time_line": time_line,
                "tags": item.get("tags") or [],
                "type": "candidate",
                "facilitator": "",
            })
            i += 1
        return entries

    @rx.var
    def facilitator_entries(self) -> list[dict]:
        entries: list[dict] = []
        i = 1
        for key, item in self.raw_facilitator_feedbacks.items():
            c_name = item.get("candidate_name") or "Candidate"
            c_id = item.get("candidate_id") or "CAND-2031"
            asmn = item.get("assessment") or "Quality"
            test_name = item.get("test") or "Formative 1"
            fac = item.get("facilitator") or "Ravi Kumar"
            fb = (item.get("feedback") or "").strip()
            preview = f'"{fb[:42]}..."' if len(fb) > 42 else (f'"{fb}"' if fb else "—")
            sub_on = item.get("updated_at") or "14 Sep 2026 10:15 PM"

            date_line = sub_on
            time_line = ""
            if " " in sub_on:
                parts = sub_on.split(" ")
                date_line = " ".join(parts[:3]) if len(parts) >= 3 else parts[0]
                time_line = " ".join(parts[3:]) if len(parts) >= 3 else parts[-1]

            entries.append({
                "id": str(i),
                "key": key,
                "candidate_name": c_name,
                "candidate_id": c_id,
                "initial": c_name[0].upper() if c_name else "C",
                "assessment": asmn,
                "test": test_name,
                "facilitator": fac,
                "rating": 0,
                "rating_str": "—",
                "star1": False,
                "star2": False,
                "star3": False,
                "star4": False,
                "star5": False,
                "feedback": fb if fb else "No feedback text provided.",
                "preview": preview,
                "submitted_on": sub_on,
                "date_line": date_line,
                "time_line": time_line,
                "tags": [],
                "type": "facilitator",
            })
            i += 1
        return entries

    @rx.var
    def filtered_entries(self) -> list[dict]:
        source = self.candidate_entries if self.active_tab == "candidate" else self.facilitator_entries
        res = []
        for e in source:
            # Filter by assessment
            if self.filter_assessment != "All Assessments" and e.get("assessment", "").lower() != self.filter_assessment.lower():
                continue
            # Filter by test
            if self.filter_test != "All Tests" and e.get("test", "").lower() != self.filter_test.lower():
                continue
            # Filter by rating (Candidate tab only)
            if self.active_tab == "candidate" and self.filter_rating != "All Ratings":
                try:
                    target_star = int(self.filter_rating.split()[0])
                    if e.get("rating") != target_star:
                        continue
                except Exception:
                    pass
            # Filter by candidate search query
            if self.search_query.strip():
                q = self.search_query.strip().lower()
                matched = (
                    q in e.get("candidate_name", "").lower()
                    or q in e.get("candidate_id", "").lower()
                    or q in e.get("assessment", "").lower()
                    or q in e.get("test", "").lower()
                    or q in e.get("feedback", "").lower()
                )
                if not matched:
                    continue
            res.append(e)
        return res

    @rx.var
    def total_candidate_count(self) -> int:
        return len(self.raw_candidate_feedbacks)

    @rx.var
    def total_facilitator_count(self) -> int:
        return len(self.raw_facilitator_feedbacks)

    @rx.var
    def current_tab_count(self) -> int:
        return len(self.filtered_entries)

    @rx.var
    def paginated_entries(self) -> list[dict]:
        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        return self.filtered_entries[start:end]

    @rx.var
    def total_pages(self) -> int:
        total = len(self.filtered_entries)
        return max(1, (total + self.items_per_page - 1) // self.items_per_page)

    @rx.var
    def pagination_info_str(self) -> str:
        total = len(self.filtered_entries)
        if total == 0:
            return "Showing 0 entries"
        start = (self.current_page - 1) * self.items_per_page + 1
        end = min(self.current_page * self.items_per_page, total)
        return f"Showing {start}–{end} of {total} entries"

    @rx.var
    def selected_entry_tags(self) -> list[str]:
        if not isinstance(self.selected_entry, dict):
            return []
        tags = self.selected_entry.get("tags")
        return list(tags) if isinstance(tags, (list, tuple)) else []

    @rx.var
    def selected_has_tags(self) -> bool:
        return len(self.selected_entry_tags) > 0

    @rx.var
    def assessment_options(self) -> list[str]:
        opts = {"All Assessments"}
        for e in self.candidate_entries + self.facilitator_entries:
            if e.get("assessment"):
                opts.add(e["assessment"])
        sorted_opts = sorted(list(opts - {"All Assessments"}))
        return ["All Assessments"] + sorted_opts

    @rx.var
    def test_options(self) -> list[str]:
        opts = {"All Tests"}
        for e in self.candidate_entries + self.facilitator_entries:
            if self.filter_assessment == "All Assessments" or e.get("assessment", "").lower() == self.filter_assessment.lower():
                if e.get("test"):
                    opts.add(e["test"])
        sorted_opts = sorted(list(opts - {"All Tests"}))
        return ["All Tests"] + sorted_opts

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.current_page = 1
        self._load_data_from_disk()
        entries = self.filtered_entries
        if entries:
            self.selected_entry = entries[0]
            self.show_details_panel = True
        else:
            self.selected_entry = {}

    def set_filter_assessment(self, val: str):
        self.filter_assessment = val
        self.filter_test = "All Tests"
        self.current_page = 1

    def set_filter_test(self, val: str):
        self.filter_test = val
        self.current_page = 1

    def set_search_query(self, val: str):
        self.search_query = val
        self.current_page = 1

    def set_filter_rating(self, val: str):
        self.filter_rating = val
        self.current_page = 1

    def set_filter_date_range(self, val: str):
        self.filter_date_range = val
        self.current_page = 1

    def reset_filters(self):
        self.filter_assessment = "All Assessments"
        self.filter_test = "All Tests"
        self.search_query = ""
        self.filter_rating = "All Ratings"
        self.filter_date_range = ""
        self.current_page = 1
        entries = self.filtered_entries
        if entries:
            self.selected_entry = entries[0]

    def select_entry(self, entry: dict):
        self.selected_entry = entry
        self.show_details_panel = True

    def close_details_panel(self):
        self.show_details_panel = False

    def set_page(self, page: int):
        self.current_page = page

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

    def export_feedback(self):
        count = len(self.filtered_entries)
        tab_name = "Candidate" if self.active_tab == "candidate" else "Facilitator"
        return rx.toast.success(f"{count} {tab_name} feedback records exported successfully!")

