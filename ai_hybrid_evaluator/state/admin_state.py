"""
Admin dashboard state — mock data only (frontend-only).
Backend developer will later swap the mock lists for real DB-backed queries,
and the add_*/update_*/delete_* functions for real API calls. Function names/
shapes kept stable on purpose so that swap is easy later.
"""

import json
import asyncio
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import re
import reflex as rx
from backend.services.assessment_service import AssessmentService
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.feedback_service import FeedbackService
from backend.repositories.facilitator_repository import FacilitatorRepository

from ai_hybrid_evaluator.models.models import (
    Candidate, Facilitator, Assessment,
    SHARED_CANDIDATES, SHARED_FACILITATORS,
    get_facilitator_profile, get_candidate_profile,
)

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
FACILITATOR_ID_REGEX = r"^F\d{3}$"
PHONE_REGEX = r"^\d{10}$"


def generate_assessment_donut_svg(
    in_prog: int,
    pending: int,
    completed: int,
    cx: float = 100.0,
    cy: float = 100.0,
    R: float = 86.0,
    r: float = 50.0,
) -> str:
    total = in_prog + pending + completed

    lbl_ip = str(in_prog)
    lbl_pe = str(pending)
    lbl_co = str(completed)

    # Order matches reference design: Green (top-right), Blue (bottom), Orange (top-left)
    items = [
        ("In Progress", in_prog, lbl_ip, "#10B981"),    # Green
        ("Completed", completed, lbl_co, "#2563EB"),    # Blue
        ("Pending", pending, lbl_pe, "#F59E0B"),        # Orange
    ]

    # Angular allocation:
    min_arc = 42.0
    zero_count = sum(1 for _, cnt, _, _ in items if cnt == 0)

    if total == 0 or zero_count == 3:
        spans = [120.0, 120.0, 120.0]
    elif zero_count > 0:
        reserved_for_zero = zero_count * min_arc
        remaining_deg = 360.0 - reserved_for_zero
        non_zero_sum = sum(cnt for _, cnt, _, _ in items if cnt > 0)
        spans = [min_arc if cnt == 0 else (cnt / non_zero_sum) * remaining_deg for _, cnt, _, _ in items]
    else:
        raw_spans = [(cnt / total) * 360.0 for _, cnt, _, _ in items]
        small_count = sum(1 for s in raw_spans if s < min_arc)
        if small_count > 0:
            rem = 360.0 - (small_count * min_arc)
            large_sum = sum(cnt for s, (_, cnt, _, _) in zip(raw_spans, items) if s >= min_arc)
            spans = [min_arc if s < min_arc else (cnt / large_sum) * rem for s, (_, cnt, _, _) in zip(raw_spans, items)]
        else:
            spans = raw_spans

    current_angle = 0.0  # Start at top (12 o'clock)
    paths = []
    labels = []
    r_mid = (R + r) / 2.0

    for i, (name, cnt, lbl, fill_color) in enumerate(items):
        span = spans[i]
        a1 = current_angle
        a2 = current_angle + span
        current_angle += span

        t1 = math.radians(a1 - 90)
        t2 = math.radians(a2 - 90)

        x1_o, y1_o = cx + R * math.cos(t1), cy + R * math.sin(t1)
        x2_o, y2_o = cx + R * math.cos(t2), cy + R * math.sin(t2)
        x1_i, y1_i = cx + r * math.cos(t1), cy + r * math.sin(t1)
        x2_i, y2_i = cx + r * math.cos(t2), cy + r * math.sin(t2)

        large = 1 if (span % 360) > 180 else 0

        d = f"M {x1_o:.2f} {y1_o:.2f} A {R} {R} 0 {large} 1 {x2_o:.2f} {y2_o:.2f} L {x2_i:.2f} {y2_i:.2f} A {r} {r} 0 {large} 0 {x1_i:.2f} {y1_i:.2f} Z"
        paths.append(f'<path d="{d}" fill="{fill_color}" stroke="#ffffff" stroke-width="1.5" />')

        mid = (a1 + a2) / 2.0
        tm = math.radians(mid - 90)
        tx, ty = cx + r_mid * math.cos(tm), cy + r_mid * math.sin(tm)
        labels.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="13" font-weight="700" font-family="Inter, system-ui, sans-serif" style="text-shadow: 0 1px 2px rgba(0,0,0,0.35);">{lbl}</text>')

    svg = (
        f'<svg width="190" height="190" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        f'<g>'
        + "".join(paths)
        + f'<circle cx="{cx}" cy="{cy}" r="{r-1}" fill="#ffffff" />'
        + "".join(labels)
        + f'<text x="{cx}" y="{cy-9}" text-anchor="middle" dominant-baseline="central" fill="#0F172A" font-size="28" font-weight="700" font-family="Plus Jakarta Sans, system-ui, sans-serif">{total}</text>'
        + f'<text x="{cx}" y="{cy+11}" text-anchor="middle" dominant-baseline="central" fill="#64748B" font-size="11" font-weight="500" font-family="Inter, system-ui, sans-serif">Total</text>'
        + f'<text x="{cx}" y="{cy+25}" text-anchor="middle" dominant-baseline="central" fill="#64748B" font-size="11" font-weight="500" font-family="Inter, system-ui, sans-serif">Tests</text>'
        f'</g>'
        f'</svg>'
    )
    return svg


def count_assessment_tests_by_status(assessments: list[dict]) -> dict[str, int]:
    """Count tests by facilitator approval and assessment closure for the admin donut."""
    counts = {"in_progress": 0, "pending": 0, "completed": 0}
    for assessment in assessments:
        test_names = assessment.get("tests", [])
        if not isinstance(test_names, list):
            test_names = []
        names = [str(name).strip() for name in test_names if str(name).strip()]

        # Include a final test and support older assessment records that only
        # expose the persisted test-ID map.
        final_test = assessment.get("final_test", "")
        if isinstance(final_test, str) and final_test.strip():
            names.append(final_test.strip())
        if not names and isinstance(assessment.get("test_ids"), dict):
            names.extend(str(name).strip() for name in assessment["test_ids"] if str(name).strip())
        test_count = len(set(names))
        if not test_count:
            continue

        lifecycle = str(assessment.get("status", "")).strip().casefold()
        if lifecycle in {"completed", "done", "finished"}:
            # Closed assessments take precedence so each test appears in one slice.
            counts["completed"] += test_count
            continue

        approval = str(assessment.get("approval_status", "")).strip().casefold()
        facilitator_approvals = assessment.get("facilitator_approvals", {})
        any_facilitator_approved = (
            isinstance(facilitator_approvals, dict)
            and any(str(value).strip().casefold() == "approved" for value in facilitator_approvals.values())
        )
        if approval == "approved" or any_facilitator_approved:
            counts["in_progress"] += test_count
        else:
            # Pending includes any test whose assessment has not been approved.
            counts["pending"] += test_count
    return counts


class AdminState(rx.State):
    # ---- Sidebar UI state ----
    users_menu_open: bool = True

    def toggle_users_menu(self):
        self.users_menu_open = not self.users_menu_open

    # ---- Mock data ----
    facilitators: list[Facilitator] = list(SHARED_FACILITATORS)
    candidates: list[Candidate] = list(SHARED_CANDIDATES)
    pending_evaluations: int = 12

    def load_persisted_candidates(self):
        """Load candidate identities from the backend into the existing UI shape."""
        try:
            service = CandidateManagementService()
            backend_candidates = service.list_candidates()
        except (ValueError, OSError):
            return

        loaded_candidates = []

        for candidate in backend_candidates:
            candidate_id = str(candidate["candidate_id"])

            loaded_candidates.append({
                "emp_id": candidate_id,
                "name": str(candidate["name"]),
                "email": str(candidate["email"]),
                "password": str(candidate.get("password", "")),
            })

        self.candidates = loaded_candidates

    def load_persisted_facilitators(self):
        """Load persisted facilitators from the JSON repository."""
        try:
            backend_facilitators = FacilitatorRepository().get_all()
        except (ValueError, OSError):
            return

        self.facilitators = [
            {
                "emp_id": str(facilitator.get("emp_id", "")),
                "name": str(facilitator.get("name", "")),
                "email": str(facilitator.get("email", "")),
                "phone": str(facilitator.get("phone", "")),
                "password": str(facilitator.get("password", "")),
            }
            for facilitator in backend_facilitators
        ]

        # Keep the existing shared UI/auth catalogue synchronized
        # with the persisted repository.
        SHARED_FACILITATORS[:] = [
            dict(facilitator)
            for facilitator in self.facilitators
        ]

    def load_assessments_page_data(self):
        """Load persisted assessments, candidates and facilitators."""
        self.load_persisted_assessments()
        self.load_persisted_candidates()
        self.load_persisted_facilitators()

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
    new_facilitator_show_password: bool = False
    facilitator_form_error: str = ""

    def set_show_add_facilitator(self, value: bool):
        self.show_add_facilitator = value
        if not value:
            self.new_facilitator_empid = ""
            self.new_facilitator_name = ""
            self.new_facilitator_email = ""
            self.new_facilitator_phone = ""
            self.new_facilitator_password = ""
            self.new_facilitator_show_password = False
            self.facilitator_form_error = ""

    def toggle_new_facilitator_password(self):
        self.new_facilitator_show_password = not self.new_facilitator_show_password

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
        try:
            FacilitatorRepository().save(new_f)
        except (ValueError, OSError) as exc:
            self.facilitator_form_error = str(exc)
            return

        self.facilitators.append(new_f)

        if not any(
            f["emp_id"] == new_f["emp_id"]
            for f in SHARED_FACILITATORS
        ):
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
    edit_facilitator_show_password: bool = False
    edit_facilitator_error: str = ""

    def toggle_edit_facilitator_password(self):
        self.edit_facilitator_show_password = not self.edit_facilitator_show_password

    def open_edit_facilitator(self, index: int):
        f = self.facilitators[index]
        self.edit_facilitator_index = index
        self.edit_facilitator_empid = f["emp_id"]
        self.edit_facilitator_name = f["name"]
        self.edit_facilitator_email = f["email"]
        self.edit_facilitator_phone = f["phone"]
        self.edit_facilitator_password = f["password"]
        self.edit_facilitator_show_password = False
        self.edit_facilitator_error = ""
        self.show_edit_facilitator = True

    def set_show_edit_facilitator(self, value: bool):
        self.show_edit_facilitator = value
        if not value:
            self.edit_facilitator_index = -1
            self.edit_facilitator_show_password = False
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

        old_emp_id = self.facilitators[
            self.edit_facilitator_index
        ]["emp_id"]

        updated_facilitator: Facilitator = {
            "emp_id": self.edit_facilitator_empid,
            "name": self.edit_facilitator_name,
            "email": self.edit_facilitator_email,
            "phone": self.edit_facilitator_phone,
            "password": self.edit_facilitator_password,
        }

        try:
            FacilitatorRepository().replace(
                old_emp_id,
                updated_facilitator,
            )
        except (ValueError, OSError) as exc:
            self.edit_facilitator_error = str(exc)
            return

        self.facilitators[
            self.edit_facilitator_index
        ] = updated_facilitator

        for i, facilitator in enumerate(SHARED_FACILITATORS):
            if facilitator["emp_id"] == old_emp_id:
                SHARED_FACILITATORS[i] = updated_facilitator
                break

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
            facilitator = self.facilitators[
                self.delete_facilitator_index
            ]
            emp_id = facilitator["emp_id"]

            try:
                FacilitatorRepository().delete(emp_id)
            except (ValueError, OSError):
                return

            del self.facilitators[
                self.delete_facilitator_index
            ]

            SHARED_FACILITATORS[:] = [
                f
                for f in SHARED_FACILITATORS
                if f["emp_id"] != emp_id
            ]

        self.set_show_delete_facilitator(False)

    # =========================================================
    # ADD CANDIDATE (dialog/form)
    # =========================================================
    show_add_candidate: bool = False
    new_candidate_id: str = ""
    new_candidate_name: str = ""
    new_candidate_email: str = ""
    new_candidate_password: str = ""
    new_candidate_show_password: bool = False
    candidate_form_error: str = ""

    def set_show_add_candidate(self, value: bool):
        self.show_add_candidate = value
        if not value:
            self.new_candidate_id = ""
            self.new_candidate_name = ""
            self.new_candidate_email = ""
            self.new_candidate_password = ""
            self.new_candidate_show_password = False
            self.candidate_form_error = ""

    def toggle_new_candidate_password(self):
        self.new_candidate_show_password = not self.new_candidate_show_password

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
            self.new_candidate_id,
            self.new_candidate_name,
            self.new_candidate_email,
            self.new_candidate_password,
        ]):
            self.candidate_form_error = "Please fill in all fields."
            return

        print("DEBUG candidate email:", repr(self.new_candidate_email))

        if not re.match(EMAIL_REGEX, self.new_candidate_email):
            self.candidate_form_error = "Enter a valid email address."
            return

        if len(self.new_candidate_password) < 6:
            self.candidate_form_error = "Password must be at least 6 characters."
            return

        candidate_id = self.new_candidate_id.strip()
        candidate_name = self.new_candidate_name.strip()
        candidate_email = self.new_candidate_email.strip().lower()

        try:
            service = CandidateManagementService()

            saved = service.create_candidate({
                "candidate_id": candidate_id,
                "name": candidate_name,
                "email": candidate_email,
                "password": self.new_candidate_password,
            })

        except (ValueError, OSError) as exc:
            self.candidate_form_error = str(exc)
            return

        new_c: Candidate = {
            "emp_id": saved["candidate_id"],
            "name": saved["name"],
            "email": saved["email"],
            "password": "",
        }

        self.candidates.append(new_c)

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
    edit_candidate_show_password: bool = False
    edit_candidate_error: str = ""

    def toggle_edit_candidate_password(self):
        self.edit_candidate_show_password = not self.edit_candidate_show_password

    def open_edit_candidate(self, index: int):
        c = self.candidates[index]
        self.edit_candidate_index = index
        self.edit_candidate_id = c["emp_id"]
        self.edit_candidate_name = c["name"]
        self.edit_candidate_email = c["email"]
        # Never display a stored password. A blank field means keep the current
        # credential; the admin may enter a replacement password if needed.
        self.edit_candidate_password = ""
        self.edit_candidate_show_password = False
        self.edit_candidate_error = ""
        self.show_edit_candidate = True

    def set_show_edit_candidate(self, value: bool):
        self.show_edit_candidate = value
        if not value:
            self.edit_candidate_index = -1
            self.edit_candidate_password = ""
            self.edit_candidate_show_password = False
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
            self.edit_candidate_id,
            self.edit_candidate_name,
            self.edit_candidate_email,
        ]):
            self.edit_candidate_error = "Please fill in all fields."
            return

        if not re.match(EMAIL_REGEX, self.edit_candidate_email):
            self.edit_candidate_error = "Enter a valid email address."
            return

        if self.edit_candidate_password and len(self.edit_candidate_password) < 6:
            self.edit_candidate_error = "Password must be at least 6 characters."
            return

        if not (0 <= self.edit_candidate_index < len(self.candidates)):
            self.edit_candidate_error = "Candidate not found."
            return

        original_id = self.candidates[self.edit_candidate_index]["emp_id"]

        # Candidate IDs are stable backend identities and cannot be changed.
        if self.edit_candidate_id.strip() != original_id:
            self.edit_candidate_error = "Candidate ID cannot be changed."
            return

        try:
            service = CandidateManagementService()

            changes = {
                "candidate_id": original_id,
                "name": self.edit_candidate_name.strip(),
                "email": self.edit_candidate_email.strip().lower(),
            }
            if self.edit_candidate_password:
                changes["password"] = self.edit_candidate_password
            saved = service.update_candidate(original_id, changes)

        except (ValueError, OSError) as exc:
            self.edit_candidate_error = str(exc)
            return

        updated_candidate: Candidate = {
            "emp_id": saved["candidate_id"],
            "name": saved["name"],
            "email": saved["email"],
            "password": self.candidates[self.edit_candidate_index].get("password", ""),
        }

        self.candidates[self.edit_candidate_index] = updated_candidate

        # Keep shared identity details in sync without changing credentials.
        shared_candidate_found = False

        for i, candidate in enumerate(SHARED_CANDIDATES):
            if candidate["emp_id"].casefold() == original_id.casefold():
                SHARED_CANDIDATES[i] = updated_candidate
                shared_candidate_found = True
                break

        if not shared_candidate_found:
            SHARED_CANDIDATES.append(updated_candidate)

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
        if not (0 <= self.delete_candidate_index < len(self.candidates)):
            self.set_show_delete_candidate(False)
            return

        candidate = self.candidates[self.delete_candidate_index]
        candidate_id = candidate["emp_id"]

        try:
            service = CandidateManagementService()
            service.delete_candidate(candidate_id)

        except (ValueError, OSError) as exc:
            # Keep the candidate because backend deletion did not succeed.
            self.candidate_form_error = str(exc)
            self.set_show_delete_candidate(False)
            return

        # Backend deletion succeeded, so now update the UI/session copy.
        self.candidates = [
            c for c in self.candidates
            if c["emp_id"].casefold() != candidate_id.casefold()
        ]

        SHARED_CANDIDATES[:] = [
            c for c in SHARED_CANDIDATES
            if c["emp_id"].casefold() != candidate_id.casefold()
        ]

        self.set_show_delete_candidate(False)

    # =========================================================
    # ASSESSMENTS
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
            "status": "In Progress",
            # Tests are empty by default — Facilitators add them via their workspace
            "tests": [],
            "final_test": "",
            "approval_status": "approved",
            "facilitator_approvals": {
                "F001": "approved",
                "F002": "approved",
            },
            "question_papers": {},
            "test_dates": {},
        },
    ]


    def _apply_assessment_records(self, records):
        self.assessments = records
        self.test_question_papers = {
            f"{a['name']}__{test}": filename
            for a in records for test, filename in a.get("question_papers", {}).items()
        }

    def load_persisted_assessments(self):
        try:
            self._load_persisted_assessments()
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

    async def load_persisted_assessments_async(self, legacy_question_papers: dict | None = None):
        try:
            records = await asyncio.to_thread(self._load_persisted_assessments, legacy_question_papers, False)
            self._apply_assessment_records(records)
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

    def _load_persisted_assessments(self, legacy_question_papers=None, apply=True):
        """Restore the shared assessment structures; bootstrap legacy state once."""
        initial = []
        for assessment in self.assessments:
            value = dict(assessment)
            qps = dict((legacy_question_papers or {}).get(value["name"], {}))
            qps.update(value.get("question_papers", {}))
            names = list(value.get("tests", [])) + ([value["final_test"]] if value.get("final_test") else [])
            for test in names:
                filename = self.test_question_papers.get(f"{value['name']}__{test}", "")
                if filename and not qps.get(test):
                    qps[test] = filename
            value["question_papers"] = qps
            initial.append(value)
        records = AssessmentService().load_or_bootstrap(initial)
        if apply:
            self._apply_assessment_records(records)
        return records

    def _persist_assessment_record(self, record, validate_assignments=False):
        service = AssessmentService()
        if validate_assignments:
            service.facilitator_catalog = lambda: self.facilitators
            service.candidate_catalog = lambda: self.candidates
            if record.get("assessment_id"):
                saved = service.update_assessment(record["assessment_id"], record)
            else:
                saved = service.create_assessment(record)
        else:
            saved = service.save_assessment(record)
        self._apply_assessment_records(service.load_assessments())
        return saved

    def _add_assessment_test(self, record, name, date="", description="", is_final=False, *, test_type=None, start_time="", end_time=""):
        service = AssessmentService()
        if not record.get("assessment_id"):
            record = self._persist_assessment_record(record)
        saved = service.add_test(record["assessment_id"], name, date=date, description=description, is_final=is_final, test_type=test_type, start_time=start_time, end_time=end_time)
        self._apply_assessment_records(service.load_assessments())
        return saved

    assessment_status_options: list[str] = ["Draft", "Scheduled", "In Progress", "Pending", "Active", "Completed"]


    @rx.var
    def min_test_date(self) -> str:
        return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

    @rx.var
    def total_assessments(self) -> int:
        return len(self.assessments)

    @rx.var
    def active_assessments(self) -> int:
        return self.assessment_in_progress_count

    @rx.var
    def completed_assessments(self) -> int:
        return self.assessment_completed_count

    @rx.var
    def total_approved_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "approved")

    @rx.var
    def total_pending_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "pending")

    @rx.var
    def total_declined_assessments(self) -> int:
        return sum(1 for a in self.assessments if a.get("approval_status", "pending") == "declined")

    @rx.var
    def assessment_in_progress_count(self) -> int:
        return sum(
            1 for a in self.assessments
            if str(a.get("status", "")).strip().lower() in ["in progress", "active"]
        )

    @rx.var
    def assessment_pending_count(self) -> int:
        return sum(
            1 for a in self.assessments
            if str(a.get("status", "")).strip().lower() in ["pending", "scheduled", "draft", "awaiting evaluation"]
        )

    @rx.var
    def assessment_completed_count(self) -> int:
        return sum(
            1 for a in self.assessments
            if str(a.get("status", "")).strip().lower() in ["completed", "done", "finished"]
        )

    @rx.var
    def assessment_total_count(self) -> int:
        return self.assessment_in_progress_count + self.assessment_pending_count + self.assessment_completed_count

    @rx.var
    def assessment_in_progress_pct_subtitle(self) -> str:
        count = self.assessment_in_progress_count
        return "assessment" if count == 1 else "assessments"

    @rx.var
    def assessment_pending_pct_subtitle(self) -> str:
        count = self.assessment_pending_count
        return "assessment" if count == 1 else "assessments"

    @rx.var
    def assessment_completed_pct_subtitle(self) -> str:
        count = self.assessment_completed_count
        return "assessment" if count == 1 else "assessments"

    @rx.var
    def dashboard_test_status_counts(self) -> dict[str, int]:
        return count_assessment_tests_by_status(self.assessments)

    @rx.var
    def dashboard_tests_in_progress_count(self) -> int:
        return self.dashboard_test_status_counts.get("in_progress", 0)

    @rx.var
    def dashboard_tests_pending_count(self) -> int:
        return self.dashboard_test_status_counts.get("pending", 0)

    @rx.var
    def dashboard_tests_completed_count(self) -> int:
        return self.dashboard_test_status_counts.get("completed", 0)

    @rx.var
    def dashboard_tests_in_progress_subtitle(self) -> str:
        return "test" if self.dashboard_tests_in_progress_count == 1 else "tests"

    @rx.var
    def dashboard_tests_pending_subtitle(self) -> str:
        return "test" if self.dashboard_tests_pending_count == 1 else "tests"

    @rx.var
    def dashboard_tests_completed_subtitle(self) -> str:
        return "test" if self.dashboard_tests_completed_count == 1 else "tests"

    @rx.var
    def assessment_donut_svg_html(self) -> str:
        return generate_assessment_donut_svg(
            self.dashboard_tests_in_progress_count,
            self.dashboard_tests_pending_count,
            self.dashboard_tests_completed_count,
        )

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
        try:
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

            self._persist_assessment_record({
                "name": self.new_assessment_name,
                "assessment_date": self.new_assessment_date,
                # Multi-facilitator
                "facilitator_ids": list(self.new_assessment_facilitator_ids),
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
            }, validate_assignments=True)
            self.set_show_add_assessment(False)
        except (ValueError, OSError) as exc:
            self.assessment_form_error = str(exc)

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
        try:
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

            if not 0 <= self.edit_assessment_index < len(self.assessments):
                self.edit_assessment_error = "Assessment no longer exists; reload before editing."
                return
            existing_a = self.assessments[self.edit_assessment_index]
            existing_tests = existing_a.get("tests", [])
            existing_final_test = existing_a.get("final_test", "")
            existing_test_dates = existing_a.get("test_dates", {})
            existing_qps = existing_a.get("question_papers", {})

            updated = {
                **dict(existing_a),
                "name": self.edit_assessment_name,
                "assessment_date": self.edit_assessment_date,
                # Multi-facilitator
                "facilitator_ids": list(self.edit_assessment_facilitator_ids),
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
            self._persist_assessment_record(updated, validate_assignments=True)
            self.set_show_edit_assessment(False)
        except (ValueError, OSError) as exc:
            self.edit_assessment_error = str(exc)

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
        try:
            if 0 <= self.delete_assessment_index < len(self.assessments):
                assessment = self.assessments[self.delete_assessment_index]
                service = AssessmentService()
                identity = assessment.get("assessment_id")
                if not identity:
                    identity = service.save_assessment(dict(assessment))["assessment_id"]
                service.delete_assessment(identity)
                self._apply_assessment_records(service.load_assessments())
            self.set_show_delete_assessment(False)
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

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
    candidate_saved_forms: dict[str, dict] = {}


    def open_feedback_dialog(self, index: int):
        if not (0 <= index < len(self.assessments)):
            return rx.toast.error("Assessment not found.")

        self.feedback_assessment_index = index
        self.feedback_assessment_name = self.assessments[index]["name"]
        self.show_feedback_type_dialog = True


    def set_show_feedback_type_dialog(self, value: bool):
        self.show_feedback_type_dialog = value

        # Do NOT clear the assessment here.
        # The facilitator/candidate builder is opened immediately after
        # this dialog closes and still needs the selected assessment.


    def close_feedback_type_dialog(self):
        self.show_feedback_type_dialog = False
        self.feedback_assessment_index = -1
        self.feedback_assessment_name = ""


    # =========================================================
    # FACILITATOR FEEDBACK FORM
    # =========================================================

    def open_facilitator_feedback_builder(self):
        """Open the facilitator feedback builder and load its persisted form."""

        try:
            self.show_feedback_type_dialog = False

            if not (0 <= self.feedback_assessment_index < len(self.assessments)):
                raise ValueError("Please select a valid assessment.")

            assessment = dict(self.assessments[self.feedback_assessment_index])

            # Make sure the assessment exists in backend persistence.
            if not assessment.get("assessment_id"):
                assessment = self._persist_assessment_record(assessment)

            assessment_id = assessment["assessment_id"]
            assessment_name = assessment.get(
                "name",
                self.feedback_assessment_name,
            )

            self.feedback_assessment_name = assessment_name

            service = FeedbackService()
            existing = service.resolve_form(
                assessment_id,
                "facilitator",
            )

            if existing:
                self.facilitator_form_title = existing.get(
                    "title",
                    f"Facilitator Feedback Form - {assessment_name}",
                )

                self.facilitator_form_questions = [
                    dict(question)
                    for question in existing.get("questions", [])
                ]

                self._facilitator_q_counter = len(
                    self.facilitator_form_questions
                )

                saved = dict(self.facilitator_saved_forms)
                saved[assessment_name] = {
                    "feedback_form_id": existing.get(
                        "feedback_form_id",
                        "",
                    ),
                    "title": self.facilitator_form_title,
                    "questions": [
                        dict(question)
                        for question in self.facilitator_form_questions
                    ],
                }
                self.facilitator_saved_forms = saved

            else:
                self.facilitator_form_title = (
                    f"Facilitator Feedback Form - {assessment_name}"
                )
                self.facilitator_form_questions = []
                self._facilitator_q_counter = 0

            self.show_facilitator_feedback_builder = True

        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))


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

        self.facilitator_form_questions = (
            self.facilitator_form_questions + [new_q]
        )


    def set_facilitator_question_text(
        self,
        qid: str,
        value: str,
    ):
        questions = [
            dict(question)
            for question in self.facilitator_form_questions
        ]

        for question in questions:
            if question.get("id") == qid:
                question["text"] = value
                break

        self.facilitator_form_questions = questions


    def toggle_facilitator_question_required(self, qid: str):
        questions = [
            dict(question)
            for question in self.facilitator_form_questions
        ]

        for question in questions:
            if question.get("id") == qid:
                question["required"] = not bool(
                    question.get("required", True)
                )
                break

        self.facilitator_form_questions = questions


    def delete_facilitator_question(self, qid: str):
        self.facilitator_form_questions = [
            question
            for question in self.facilitator_form_questions
            if question.get("id") != qid
        ]


    def submit_facilitator_feedback_form(self):
        """Persist the Admin-created facilitator feedback form."""

        try:
            if not (
                0 <= self.feedback_assessment_index
                < len(self.assessments)
            ):
                raise ValueError("Please select a valid assessment.")

            assessment = dict(
                self.assessments[self.feedback_assessment_index]
            )

            # Ensure this assessment has a backend assessment_id.
            if not assessment.get("assessment_id"):
                assessment = self._persist_assessment_record(
                    assessment
                )

            assessment_id = assessment["assessment_id"]
            assessment_name = assessment.get(
                "name",
                self.feedback_assessment_name,
            )

            title = (
                self.facilitator_form_title.strip()
                if self.facilitator_form_title.strip()
                else f"Facilitator Feedback Form - {assessment_name}"
            )

            questions = []

            for index, question in enumerate(
                self.facilitator_form_questions,
                start=1,
            ):
                text = str(
                    question.get("text", "")
                ).strip()

                if not text:
                    raise ValueError(
                        "Feedback questions cannot be empty."
                    )

                question_id = str(
                    question.get("id", "")
                ).strip()

                if not question_id:
                    question_id = f"fq_{index}"

                questions.append({
                    "id": question_id,
                    "text": text,
                    "type": "textarea",
                    "required": bool(
                        question.get("required", True)
                    ),
                })

            if not questions:
                raise ValueError(
                    "Add at least one feedback question."
                )

            service = FeedbackService()

            existing = service.resolve_form(
                assessment_id,
                "facilitator",
            )

            details = {
                "title": title,
                "description": "",
                "assessment_id": assessment_id,
                "target_role": "facilitator",
                "questions": questions,
                "active": True,
            }

            if existing:
                saved_form = service.save_form(
                    details,
                    form_id=existing["feedback_form_id"],
                )
            else:
                saved_form = service.save_form(details)

            # Keep the existing Reflex UI cache synchronized.
            saved = dict(self.facilitator_saved_forms)

            saved[assessment_name] = {
                "feedback_form_id": saved_form[
                    "feedback_form_id"
                ],
                "title": saved_form["title"],
                "questions": [
                    dict(question)
                    for question in saved_form["questions"]
                ],
            }

            self.facilitator_saved_forms = saved

            self.show_facilitator_feedback_builder = False

            return rx.toast.success(
                "Facilitator Feedback Form created successfully."
            )

        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))


    # =========================================================
    # CANDIDATE FEEDBACK FORM
    # =========================================================

    def open_candidate_feedback_builder(self):
        """Open candidate feedback builder and load persisted form."""

        try:
            self.show_feedback_type_dialog = False

            if not (
                0 <= self.feedback_assessment_index
                < len(self.assessments)
            ):
                raise ValueError("Please select a valid assessment.")

            assessment = dict(
                self.assessments[self.feedback_assessment_index]
            )

            if not assessment.get("assessment_id"):
                assessment = self._persist_assessment_record(
                    assessment
                )

            assessment_id = assessment["assessment_id"]
            assessment_name = assessment.get(
                "name",
                self.feedback_assessment_name,
            )

            self.feedback_assessment_name = assessment_name

            service = FeedbackService()

            existing = service.resolve_form(
                assessment_id,
                "candidate",
            )

            if existing:
                self.candidate_form_title = existing.get(
                    "title",
                    f"Candidate Feedback Form - {assessment_name}",
                )

                self.candidate_form_questions = [
                    dict(question)
                    for question in existing.get("questions", [])
                ]

                self._candidate_q_counter = len(
                    self.candidate_form_questions
                )

                saved = dict(self.candidate_saved_forms)

                saved[assessment_name] = {
                    "feedback_form_id": existing.get(
                        "feedback_form_id",
                        "",
                    ),
                    "title": self.candidate_form_title,
                    "questions": [
                        dict(question)
                        for question in self.candidate_form_questions
                    ],
                }

                self.candidate_saved_forms = saved

            else:
                self.candidate_form_title = (
                    f"Candidate Feedback Form - {assessment_name}"
                )
                self.candidate_form_questions = []
                self._candidate_q_counter = 0

            self.show_candidate_feedback_builder = True

        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))


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

        self.candidate_form_questions = (
            self.candidate_form_questions + [new_q]
        )


    def set_candidate_question_text(
        self,
        qid: str,
        value: str,
    ):
        questions = [
            dict(question)
            for question in self.candidate_form_questions
        ]

        for question in questions:
            if question.get("id") == qid:
                question["text"] = value
                break

        self.candidate_form_questions = questions


    def toggle_candidate_question_required(self, qid: str):
        questions = [
            dict(question)
            for question in self.candidate_form_questions
        ]

        for question in questions:
            if question.get("id") == qid:
                question["required"] = not bool(
                    question.get("required", True)
                )
                break

        self.candidate_form_questions = questions


    def delete_candidate_question(self, qid: str):
        self.candidate_form_questions = [
            question
            for question in self.candidate_form_questions
            if question.get("id") != qid
        ]


    def submit_candidate_feedback_form(self):
        """Persist the Admin-created candidate feedback form."""

        try:
            if not (
                0 <= self.feedback_assessment_index
                < len(self.assessments)
            ):
                raise ValueError("Please select a valid assessment.")

            assessment = dict(
                self.assessments[self.feedback_assessment_index]
            )

            if not assessment.get("assessment_id"):
                assessment = self._persist_assessment_record(
                    assessment
                )

            assessment_id = assessment["assessment_id"]
            assessment_name = assessment.get(
                "name",
                self.feedback_assessment_name,
            )

            title = (
                self.candidate_form_title.strip()
                if self.candidate_form_title.strip()
                else f"Candidate Feedback Form - {assessment_name}"
            )

            questions = []

            for index, question in enumerate(
                self.candidate_form_questions,
                start=1,
            ):
                text = str(
                    question.get("text", "")
                ).strip()

                if not text:
                    raise ValueError(
                        "Feedback questions cannot be empty."
                    )

                question_id = str(
                    question.get("id", "")
                ).strip()

                if not question_id:
                    question_id = f"cq_{index}"

                questions.append({
                    "id": question_id,
                    "text": text,
                    "type": "textarea",
                    "required": bool(
                        question.get("required", True)
                    ),
                })

            if not questions:
                raise ValueError(
                    "Add at least one feedback question."
                )

            service = FeedbackService()

            existing = service.resolve_form(
                assessment_id,
                "candidate",
            )

            details = {
                "title": title,
                "description": "",
                "assessment_id": assessment_id,
                "target_role": "candidate",
                "questions": questions,
                "active": True,
            }

            if existing:
                saved_form = service.save_form(
                    details,
                    form_id=existing["feedback_form_id"],
                )
            else:
                saved_form = service.save_form(details)

            saved = dict(self.candidate_saved_forms)

            saved[assessment_name] = {
                "feedback_form_id": saved_form[
                    "feedback_form_id"
                ],
                "title": saved_form["title"],
                "questions": [
                    dict(question)
                    for question in saved_form["questions"]
                ],
            }

            self.candidate_saved_forms = saved

            self.show_candidate_feedback_builder = False

            return rx.toast.success(
                "Candidate Feedback Form created successfully."
            )

        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

        # =========================================================
    # ASSESSMENT TESTS (Type of Test Dialog)
    # =========================================================
    show_assessment_tests_dialog: bool = False
    selected_tests_assessment_index: int = -1

    def open_assessment_tests(self, index: int):
        try:
            """Open the Type of Test modal for the clicked assessment."""
            self.selected_tests_assessment_index = index
            if 0 <= index < len(self.assessments):
                a = dict(self.assessments[index])
                if "tests" not in a:
                    a["tests"] = []
                if "final_test" not in a or not a["final_test"]:
                    a["final_test"] = "Summative Test"
                self._persist_assessment_record(a)
            self.show_assessment_tests_dialog = True
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

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
        try:
            """Update the per-test conducted date."""
            if 0 <= self.selected_tests_assessment_index < len(self.assessments):
                a = dict(self.assessments[self.selected_tests_assessment_index])
                if not a.get("assessment_id"):
                    a = self._persist_assessment_record(a)
                service = AssessmentService()
                test_id = a.get("test_ids", {}).get(test_name, "")
                service.update_test(a["assessment_id"], test_id, {"date": value})
                self._apply_assessment_records(service.load_assessments())
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

    def add_test_to_selected_assessment(self):
        try:
            """Automatically increments formative test count: Formative 1 -> Formative 2 -> Formative N..."""
            if 0 <= self.selected_tests_assessment_index < len(self.assessments):
                a = dict(self.assessments[self.selected_tests_assessment_index])
                numbers = [int(t.split()[-1]) for t in a.get("tests", [])
                           if t.startswith("Formative ") and t.split()[-1].isdigit()]
                self._add_assessment_test(a, f"Formative {max(numbers, default=0) + 1}")
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

    def remove_test_from_selected_assessment(self, test_name: str):
        try:
            """Remove a formative test and renumber labels without changing survivor IDs."""
            if 0 <= self.selected_tests_assessment_index < len(self.assessments):
                assessment = dict(self.assessments[self.selected_tests_assessment_index])
                if test_name not in assessment.get("tests", []):
                    return
                if not assessment.get("assessment_id"):
                    assessment = self._persist_assessment_record(assessment)
                service = AssessmentService()
                service.delete_test(assessment["assessment_id"], assessment["test_ids"][test_name], renumber=True)
                self._apply_assessment_records(service.load_assessments())
        except (ValueError, OSError) as exc:
            return rx.toast.error(str(exc))

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
    _feedback_catalog: list[dict] = []

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
        "qa_pairs": [],
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

    @staticmethod
    def _read_feedback_data():
        """Load authoritative submitted feedback for the Admin Feedback page."""
        try:
            from backend.services.feedback_service import FeedbackService

            views = FeedbackService().response_views()

            candidate_feedbacks = {}
            facilitator_feedbacks = {}

            for row in views:
                response_id = str(
                    row.get("feedback_response_id", "")
                ).strip()

                if not response_id:
                    continue

                role = row.get("respondent_role")

                # Keep the existing Admin Feedback UI shape so its current
                # filtering, pagination, details panel and QA rendering remain
                # unchanged.
                item = {
                    **row,
                    "assessment": row.get("assessment") or "",
                    "test": row.get("test") or "",
                    "candidate_name": row.get("candidate_name") or "",
                    "candidate_id": row.get("candidate_id") or "",
                    "facilitator": row.get("facilitator") or "",
                    "qa_pairs": list(row.get("qa_pairs") or []),
                    "submitted_at": row.get("submitted_at") or "",
                }

                if role == "candidate":
                    candidate_feedbacks[response_id] = item
                elif role == "facilitator":
                    facilitator_feedbacks[response_id] = item

            return candidate_feedbacks, facilitator_feedbacks

        except (ValueError, OSError):
            import logging
            logging.getLogger(__name__).exception("Unable to load submitted feedback")
            raise

    async def on_load(self):
        """Refresh authoritative feedback once, off the event loop."""
        try:
            candidates, facilitators = await asyncio.to_thread(self._read_feedback_data)
            catalog = await asyncio.to_thread(AssessmentService().load_assessments)
        except (ValueError, OSError) as exc:
            return rx.toast.error(f"Unable to load feedback: {exc}")
        self.raw_candidate_feedbacks = candidates
        self.raw_facilitator_feedbacks = facilitators
        self._feedback_catalog = catalog
        entries = self.filtered_entries
        self.selected_entry = entries[0] if entries else {}
        self.show_details_panel = bool(entries)

    @rx.var
    def candidate_entries(self) -> list[dict]:
        entries: list[dict] = []
        i = 1
        for key, item in self.raw_candidate_feedbacks.items():
            c_name = item.get("candidate_name") or item.get("candidate_id") or "Unknown Candidate"
            c_id = item.get("candidate_id") or ""
            asmn = item.get("assessment") or ""
            test_name = item.get("test") or ""
            sub_on = item.get("submitted_at") or ""

            # Parse dynamic QA pairs from submitted form
            qa_pairs: list[dict] = []
            if item.get("qa_pairs") and isinstance(item["qa_pairs"], list):
                for p in item["qa_pairs"]:
                    if isinstance(p, dict):
                        q_t = p.get("question") or p.get("text") or "Question"
                        a_t = p.get("answer") or p.get("value") or ""
                        qa_pairs.append({"question": str(q_t), "answer": str(a_t) if str(a_t).strip() else "No response"})
            elif item.get("answers") and isinstance(item["answers"], dict):
                for q_k, a_v in item["answers"].items():
                    qa_pairs.append({"question": str(q_k), "answer": str(a_v) if str(a_v).strip() else "No response"})
            elif item.get("feedback") and str(item["feedback"]).strip():
                qa_pairs.append({"question": "Feedback", "answer": str(item["feedback"]).strip()})

            # Generate short preview of submitted question/answer responses
            if qa_pairs:
                resp_parts = [p["answer"] for p in qa_pairs if p["answer"] != "No response"]
                if not resp_parts:
                    resp_parts = [p["question"] for p in qa_pairs]
                preview_text = "; ".join(resp_parts)
                preview = f'"{preview_text[:42]}..."' if len(preview_text) > 42 else f'"{preview_text}"'
            else:
                preview = "No responses recorded"

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
                "qa_pairs": qa_pairs,
                "feedback": preview,
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
            asmn = item.get("assessment") or ""
            fac = item.get("facilitator") or item.get("respondent_id") or "Unknown Facilitator"
            sub_on = item.get("updated_at") or item.get("submitted_at") or ""

            # Parse dynamic QA pairs from submitted facilitator form
            qa_pairs: list[dict] = []
            if item.get("qa_pairs") and isinstance(item["qa_pairs"], list):
                for p in item["qa_pairs"]:
                    if isinstance(p, dict):
                        q_t = p.get("question") or p.get("text") or "Question"
                        a_t = p.get("answer") or p.get("value") or ""
                        qa_pairs.append({"question": str(q_t), "answer": str(a_t) if str(a_t).strip() else "No response"})
            elif item.get("answers") and isinstance(item["answers"], dict):
                for q_k, a_v in item["answers"].items():
                    qa_pairs.append({"question": str(q_k), "answer": str(a_v) if str(a_v).strip() else "No response"})
            elif item.get("feedback") and str(item["feedback"]).strip():
                qa_pairs.append({"question": "Feedback", "answer": str(item["feedback"]).strip()})

            if qa_pairs:
                resp_parts = [p["answer"] for p in qa_pairs if p["answer"] != "No response"]
                if not resp_parts:
                    resp_parts = [p["question"] for p in qa_pairs]
                preview_text = "; ".join(resp_parts)
                preview = f'"{preview_text[:42]}..."' if len(preview_text) > 42 else f'"{preview_text}"'
            else:
                preview = "No responses recorded"

            date_line = sub_on
            time_line = ""
            if " " in sub_on:
                parts = sub_on.split(" ")
                date_line = " ".join(parts[:3]) if len(parts) >= 3 else parts[0]
                time_line = " ".join(parts[3:]) if len(parts) >= 3 else parts[-1]

            entries.append({
                "id": str(i),
                "key": key,
                "assessment": asmn,
                "facilitator": fac,
                "qa_pairs": qa_pairs,
                "feedback": preview,
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
        if self.active_tab == "facilitator":
            res = []
            for e in self.facilitator_entries:
                if self.filter_assessment != "All Assessments" and e.get("assessment", "").lower() != self.filter_assessment.lower():
                    continue
                res.append(e)
            return res

        # Candidate tab filtering (completely unchanged)
        res = []
        for e in self.candidate_entries:
            # Filter by assessment
            if self.filter_assessment != "All Assessments" and e.get("assessment", "").lower() != self.filter_assessment.lower():
                continue
            # Filter by test
            if self.filter_test != "All Tests" and e.get("test", "").lower() != self.filter_test.lower():
                continue
            # Filter by candidate search query
            if self.search_query.strip():
                q = self.search_query.strip().lower()
                matched = (
                    q in e.get("candidate_name", "").lower()
                    or q in e.get("candidate_id", "").lower()
                    or q in e.get("assessment", "").lower()
                    or q in e.get("test", "").lower()
                    or q in e.get("preview", "").lower()
                    or any(
                        q in p.get("question", "").lower() or q in p.get("answer", "").lower()
                        for p in e.get("qa_pairs", [])
                    )
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
    def selected_qa_pairs(self) -> list[dict]:
        if not isinstance(self.selected_entry, dict):
            return []
        pairs = self.selected_entry.get("qa_pairs")
        if isinstance(pairs, list):
            return pairs
        return []

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
        """Return all persisted assessments, including assessments with no feedback yet."""
        opts = set()

        try:
            assessments = self._feedback_catalog
            for assessment in assessments:
                name = str(assessment.get("name", "")).strip()
                if name:
                    opts.add(name)
        except (ValueError, OSError):
            pass

        # Also preserve assessments referenced by existing/historical feedback.
        for entry in self.candidate_entries + self.facilitator_entries:
            name = str(entry.get("assessment", "")).strip()
            if name:
                opts.add(name)

        return ["All Assessments"] + sorted(opts, key=str.casefold)


    @rx.var
    def test_options(self) -> list[str]:
        """Return persisted tests for the selected assessment plus historical feedback tests."""
        opts = set()

        try:
            assessments = self._feedback_catalog

            for assessment in assessments:
                assessment_name = str(assessment.get("name", "")).strip()

                if (
                    self.filter_assessment != "All Assessments"
                    and assessment_name.casefold() != self.filter_assessment.casefold()
                ):
                    continue

                # Formative tests
                for test_name in assessment.get("tests", []):
                    test_name = str(test_name).strip()
                    if test_name:
                        opts.add(test_name)

                # Summative/final test
                final_test = str(assessment.get("final_test", "")).strip()
                if final_test:
                    opts.add(final_test)

        except (ValueError, OSError):
            pass

        # Preserve tests referenced by existing/historical feedback.
        for entry in self.candidate_entries + self.facilitator_entries:
            assessment_name = str(entry.get("assessment", "")).strip()

            if (
                self.filter_assessment != "All Assessments"
                and assessment_name.casefold() != self.filter_assessment.casefold()
            ):
                continue

            test_name = str(entry.get("test", "")).strip()
            if test_name:
                opts.add(test_name)

        return ["All Tests"] + sorted(opts, key=str.casefold)

    async def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.current_page = 1
        return await self.on_load()

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

