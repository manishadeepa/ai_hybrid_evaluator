"""
Admin dashboard state — mock data only (frontend-only).
Backend developer will later swap the mock lists for real DB-backed queries,
and the add_*/update_*/delete_* functions for real API calls. Function names/
shapes kept stable on purpose so that swap is easy later.
"""

import re
import reflex as rx

from ai_hybrid_evaluator.models.models import (
    Candidate, Facilitator, Assessment,
    SHARED_CANDIDATES, SHARED_FACILITATORS,
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
            "assessment_date": "2026-08-25",
            "facilitator_id": "F001",
            "facilitator_name": "Ravi Kumar",
            "assigned_candidates": ["CAND-2031", "CAND-2054", "CAND-2061"],
            "status": "Scheduled",
            "tests": ["Test 1"],
            "final_test": "Final Test",
            "approval_status": "pending",
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
    new_assessment_facilitator_id: str = ""
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
            self.new_assessment_facilitator_id = ""
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

    def set_new_assessment_facilitator_id(self, value: str):
        self.new_assessment_facilitator_id = value

    def set_new_assessment_status(self, value: str):
        self.new_assessment_status = value

    # ---- Facilitator searchable dropdown — Add form ----
    def set_add_facilitator_search(self, value: str):
        self.add_facilitator_search = value

    def toggle_add_facilitator_dropdown(self):
        self.show_add_facilitator_dropdown = not self.show_add_facilitator_dropdown
        if self.show_add_facilitator_dropdown:
            self.add_facilitator_search = ""

    def select_add_facilitator(self, facilitator_id: str):
        """Select a facilitator, close the dropdown, and clear search."""
        self.new_assessment_facilitator_id = facilitator_id
        self.show_add_facilitator_dropdown = False
        self.add_facilitator_search = ""

    # ---- Candidate multi-select search — Add form ----
    def set_add_candidate_search(self, value: str):
        self.add_candidate_search = value

    def toggle_add_candidate_dropdown(self):
        """Open/close the candidate multi-select panel in the Add Assessment form."""
        self.show_add_candidate_dropdown = not self.show_add_candidate_dropdown
        if not self.show_add_candidate_dropdown:
            self.add_candidate_search = ""

    def toggle_new_assessment_candidate(self, candidate_id: str, checked: bool):
        if checked:
            if candidate_id not in self.new_assessment_candidate_ids:
                self.new_assessment_candidate_ids.append(candidate_id)
        else:
            if candidate_id in self.new_assessment_candidate_ids:
                self.new_assessment_candidate_ids.remove(candidate_id)

    # ---- Computed filter vars — Add form ----
    @rx.var
    def filtered_add_facilitators(self) -> list[Facilitator]:
        q = self.add_facilitator_search.lower().strip()
        if not q:
            return self.facilitators
        return [f for f in self.facilitators if q in f["name"].lower() or q in f["emp_id"].lower()]

    @rx.var
    def selected_add_facilitator_name(self) -> str:
        if not self.new_assessment_facilitator_id:
            return ""
        match = next((f for f in self.facilitators if f["emp_id"] == self.new_assessment_facilitator_id), None)
        return match["name"] if match else ""

    @rx.var
    def filtered_add_candidates(self) -> list[Candidate]:
        q = self.add_candidate_search.lower().strip()
        if not q:
            return self.candidates
        return [c for c in self.candidates if q in c["name"].lower() or q in c["emp_id"].lower()]

    def add_assessment(self):
        if not self.new_assessment_name or not self.new_assessment_date or not self.new_assessment_facilitator_id:
            self.assessment_form_error = "Please fill in name, date, and facilitator."
            return

        facilitator = next(
            (f for f in self.facilitators if f["emp_id"] == self.new_assessment_facilitator_id),
            None,
        )
        if facilitator is None:
            self.assessment_form_error = "Selected facilitator not found."
            return

        self.assessments.append({
            "name": self.new_assessment_name,
            "assessment_date": self.new_assessment_date,
            "facilitator_id": self.new_assessment_facilitator_id,
            "facilitator_name": facilitator["name"],
            "assigned_candidates": list(self.new_assessment_candidate_ids),
            "status": self.new_assessment_status,
            "tests": ["Test 1"],
            "final_test": "Final Test",
            "approval_status": "pending",
        })
        self.set_show_add_assessment(False)

    # =========================================================
    # EDIT ASSESSMENT (dialog/form)
    # =========================================================
    show_edit_assessment: bool = False
    edit_assessment_index: int = -1
    edit_assessment_name: str = ""
    edit_assessment_date: str = ""
    edit_assessment_facilitator_id: str = ""
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
        self.edit_assessment_date = a["assessment_date"]
        self.edit_assessment_facilitator_id = a["facilitator_id"]
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

    def set_edit_assessment_facilitator_id(self, value: str):
        self.edit_assessment_facilitator_id = value

    def set_edit_assessment_status(self, value: str):
        self.edit_assessment_status = value

    # ---- Facilitator searchable dropdown — Edit form ----
    def set_edit_facilitator_search(self, value: str):
        self.edit_facilitator_search = value

    def toggle_edit_facilitator_dropdown(self):
        self.show_edit_facilitator_dropdown = not self.show_edit_facilitator_dropdown
        if self.show_edit_facilitator_dropdown:
            self.edit_facilitator_search = ""

    def select_edit_facilitator(self, facilitator_id: str):
        """Select a facilitator, close the dropdown, and clear search."""
        self.edit_assessment_facilitator_id = facilitator_id
        self.show_edit_facilitator_dropdown = False
        self.edit_facilitator_search = ""

    # ---- Candidate search — Edit form ----
    def set_edit_candidate_search(self, value: str):
        self.edit_candidate_search = value

    def toggle_edit_assessment_candidate(self, candidate_id: str, checked: bool):
        if checked:
            if candidate_id not in self.edit_assessment_candidate_ids:
                self.edit_assessment_candidate_ids.append(candidate_id)
        else:
            if candidate_id in self.edit_assessment_candidate_ids:
                self.edit_assessment_candidate_ids.remove(candidate_id)

    # ---- Computed filter vars — Edit form ----
    @rx.var
    def filtered_edit_facilitators(self) -> list[Facilitator]:
        q = self.edit_facilitator_search.lower().strip()
        if not q:
            return self.facilitators
        return [f for f in self.facilitators if q in f["name"].lower() or q in f["emp_id"].lower()]

    @rx.var
    def selected_edit_facilitator_name(self) -> str:
        if not self.edit_assessment_facilitator_id:
            return ""
        match = next((f for f in self.facilitators if f["emp_id"] == self.edit_assessment_facilitator_id), None)
        return match["name"] if match else ""

    @rx.var
    def filtered_edit_candidates(self) -> list[Candidate]:
        q = self.edit_candidate_search.lower().strip()
        if not q:
            return self.candidates
        return [c for c in self.candidates if q in c["name"].lower() or q in c["emp_id"].lower()]

    def save_edit_assessment(self):
        if not self.edit_assessment_name or not self.edit_assessment_date or not self.edit_assessment_facilitator_id:
            self.edit_assessment_error = "Please fill in name, date, and facilitator."
            return

        facilitator = next(
            (f for f in self.facilitators if f["emp_id"] == self.edit_assessment_facilitator_id),
            None,
        )
        if facilitator is None:
            self.edit_assessment_error = "Selected facilitator not found."
            return

        existing_a = self.assessments[self.edit_assessment_index]
        existing_tests = existing_a.get("tests", ["Test 1"])
        existing_final_test = existing_a.get("final_test", "Final Test")

        self.assessments[self.edit_assessment_index] = {
            "name": self.edit_assessment_name,
            "assessment_date": self.edit_assessment_date,
            "facilitator_id": self.edit_assessment_facilitator_id,
            "facilitator_name": facilitator["name"],
            "assigned_candidates": list(self.edit_assessment_candidate_ids),
            "status": self.edit_assessment_status,
            "tests": existing_tests,
            "final_test": existing_final_test,
            "approval_status": "pending",
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
    # ASSESSMENT TESTS (Type of Test Dialog)
    # =========================================================
    show_assessment_tests_dialog: bool = False
    selected_tests_assessment_index: int = -1

    def open_assessment_tests(self, index: int):
        """Open the Type of Test modal for the clicked assessment."""
        self.selected_tests_assessment_index = index
        if 0 <= index < len(self.assessments):
            a = dict(self.assessments[index])
            if "tests" not in a or not a["tests"]:
                a["tests"] = ["Test 1"]
            if "final_test" not in a or not a["final_test"]:
                a["final_test"] = "Final Test"
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
            return self.assessments[self.selected_tests_assessment_index].get("tests", ["Test 1"])
        return ["Test 1"]

    @rx.var
    def current_assessment_final_test(self) -> str:
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            return self.assessments[self.selected_tests_assessment_index].get("final_test", "Final Test")
        return "Final Test"

    def add_test_to_selected_assessment(self):
        """Automatically increments test count: Test 1 -> Test 2 -> Test 3..."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = dict(self.assessments[self.selected_tests_assessment_index])
            current_list = list(a.get("tests", []))
            if not current_list:
                current_list = ["Test 1"]
            next_num = len(current_list) + 1
            current_list.append(f"Test {next_num}")
            a["tests"] = current_list
            self.assessments[self.selected_tests_assessment_index] = a

    def remove_test_from_selected_assessment(self, test_name: str):
        """Removes a test (keeping at least Test 1)."""
        if 0 <= self.selected_tests_assessment_index < len(self.assessments):
            a = dict(self.assessments[self.selected_tests_assessment_index])
            current_list = list(a.get("tests", []))
            if len(current_list) > 1 and test_name in current_list:
                current_list.remove(test_name)
                # Re-number remaining tests nicely: Test 1, Test 2, ...
                renumbered = [f"Test {i + 1}" for i in range(len(current_list))]
                a["tests"] = renumbered
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
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            return self.assessments[self.viewing_test_assessment_index]["assessment_date"]
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
    def viewing_test_candidates_list(self) -> list[Candidate]:
        if 0 <= self.viewing_test_assessment_index < len(self.assessments):
            c_ids = self.assessments[self.viewing_test_assessment_index]["assigned_candidates"]
            return [c for c in self.candidates if c["emp_id"] in c_ids]
        return []

    @rx.var
    def viewing_test_is_final(self) -> bool:
        return self.viewing_test_name.lower() == "final test"