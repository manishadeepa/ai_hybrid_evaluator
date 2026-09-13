"""
Auth state — holds form values and drives sign in / sign up.
Calls into services/mock_api.py so the mock logic stays out of the UI layer.
"""

import re
import reflex as rx
from ai_hybrid_evaluator.services.mock_api import mock_login, mock_signup, change_admin_password, EMAIL_REGEX
from ai_hybrid_evaluator.models.models import SHARED_CANDIDATES, SHARED_FACILITATORS
from ai_hybrid_evaluator.state.admin_state import AdminState


class AuthState(rx.State):
    # ---- Sign In form (Admin) ----
    signin_email: str = ""
    signin_password: str = ""
    signin_error: str = ""

    # ---- Change Password form (Admin) ----
    chpwd_email: str = ""
    chpwd_current: str = ""
    chpwd_new: str = ""
    chpwd_confirm: str = ""
    chpwd_error: str = ""
    chpwd_open: bool = False

    # ---- Sign Up form (Admin) ----
    signup_username: str = ""
    signup_employee_id: str = ""
    signup_email: str = ""
    signup_password: str = ""
    signup_confirm_password: str = ""
    signup_error: str = ""
    signup_success: bool = False

    # ---- Session (Admin) ----
    is_authenticated: bool = False
    admin_name: str = ""
    admin_employee_id: str = ""
    admin_email: str = ""

    # ---- Facilitator sign-in (Facilitator ID + Password created by Admin) ----
    facilitator_signin_id: str = ""
    facilitator_signin_password: str = ""
    facilitator_signin_email: str = ""
    facilitator_signin_error: str = ""
    facilitator_access_denied: bool = False
    is_facilitator_authenticated: bool = False
    facilitator_name: str = ""
    facilitator_email: str = ""
    facilitator_emp_id: str = ""

    # ---- Candidate sign-in (Employee ID + Password created by Admin) ----
    candidate_signin_id: str = ""
    candidate_signin_password: str = ""
    candidate_signin_error: str = ""
    is_candidate_authenticated: bool = False
    candidate_name: str = ""
    candidate_emp_id: str = ""
    candidate_email: str = ""

    # ---- Password Visibility Toggles ----
    show_signin_password: bool = False
    show_facilitator_signin_password: bool = False
    show_candidate_signin_password: bool = False
    show_signup_password: bool = False
    show_signup_confirm_password: bool = False
    show_chpwd_current: bool = False
    show_chpwd_new: bool = False
    show_chpwd_confirm: bool = False

    def toggle_signin_password(self):
        self.show_signin_password = not self.show_signin_password

    def toggle_facilitator_signin_password(self):
        self.show_facilitator_signin_password = not self.show_facilitator_signin_password

    def toggle_candidate_signin_password(self):
        self.show_candidate_signin_password = not self.show_candidate_signin_password

    def toggle_signup_password(self):
        self.show_signup_password = not self.show_signup_password

    def toggle_signup_confirm_password(self):
        self.show_signup_confirm_password = not self.show_signup_confirm_password

    def toggle_chpwd_current(self):
        self.show_chpwd_current = not self.show_chpwd_current

    def toggle_chpwd_new(self):
        self.show_chpwd_new = not self.show_chpwd_new

    def toggle_chpwd_confirm(self):
        self.show_chpwd_confirm = not self.show_chpwd_confirm

    @rx.var
    def admin_avatar_initial(self) -> str:
        name = self.admin_name.strip()
        if name:
            return name[0].upper()
        return "A"

    # ---- Field setters ----
    def on_signin_page_load(self):
        """Clear any stale error when the Sign In page loads."""
        self.signin_error = ""
        self.signin_email = ""
        self.signin_password = ""

    def set_signin_email(self, value: str):
        self.signin_email = value
        self.signin_error = ""  # hide error as user types

    def set_signin_password(self, value: str):
        self.signin_password = value
        self.signin_error = ""  # hide error as user types

    def set_signup_username(self, value: str):
        self.signup_username = value

    def set_signup_employee_id(self, value: str):
        self.signup_employee_id = value

    def set_signup_email(self, value: str):
        self.signup_email = value

    def set_signup_password(self, value: str):
        self.signup_password = value

    def set_signup_confirm_password(self, value: str):
        self.signup_confirm_password = value

    def set_facilitator_signin_id(self, value: str):
        self.facilitator_signin_id = value
        self.facilitator_signin_error = ""
        self.facilitator_access_denied = False

    def set_facilitator_signin_password(self, value: str):
        self.facilitator_signin_password = value
        self.facilitator_signin_error = ""

    def set_facilitator_signin_email(self, value: str):
        self.facilitator_signin_email = value
        self.facilitator_signin_error = ""
        self.facilitator_access_denied = False

    # ---- Actions ----
    def handle_admin_keydown(self, key: str):
        if key == "Enter":
            return self.sign_in()

    async def handle_facilitator_keydown(self, key: str):
        if key == "Enter":
            return await self.facilitator_sign_in()

    async def handle_candidate_keydown(self, key: str):
        if key == "Enter":
            return await self.candidate_sign_in()

    def sign_in(self):
        self.signin_error = ""
        email = self.signin_email.strip()
        password = self.signin_password.strip()
        if not email or not password:
            self.signin_error = "Invalid Admin email or password."
            return

        result = mock_login(email, password)
        if result["success"]:
            self.signin_error = ""
            self.is_authenticated = True
            self.admin_name = result.get("employee_name", "Admin")
            self.admin_employee_id = result.get("employee_id", "")
            self.admin_email = result.get("employee_mail", "")
            return rx.redirect("/admin/dashboard")
        self.signin_error = result["error"]

    def sign_up(self):
        result = mock_signup(
            self.signup_username,
            self.signup_employee_id,
            self.signup_email,
            self.signup_password,
            self.signup_confirm_password,
        )
        if result["success"]:
            self.signup_error = ""
            self.signup_success = True
        else:
            self.signup_error = result["error"]
            self.signup_success = False

    def continue_to_signin(self):
        # reset the form, then send them to sign in
        self.signup_success = False
        self.signup_username = ""
        self.signup_employee_id = ""
        self.signup_email = ""
        self.signup_password = ""
        self.signup_confirm_password = ""
        return rx.redirect("/signin")

    def logout(self):
        self.is_authenticated = False
        self.admin_name = ""
        self.admin_employee_id = ""
        self.admin_email = ""
        return rx.redirect("/signin")

    # ---- Change Password (Admin) ----
    def open_change_password(self):
        """Reset form fields and open the dialog."""
        self.chpwd_email = ""
        self.chpwd_current = ""
        self.chpwd_new = ""
        self.chpwd_confirm = ""
        self.chpwd_error = ""
        self.chpwd_open = True

    def set_chpwd_open(self, value: bool):
        """Called by on_open_change — value is True (opening) or False (closing)."""
        self.chpwd_open = value
        if not value:
            # Reset when dialog is dismissed (Escape, outside click, Cancel)
            self.chpwd_error = ""
            self.chpwd_email = ""
            self.chpwd_current = ""
            self.chpwd_new = ""
            self.chpwd_confirm = ""

    def set_chpwd_email(self, v: str):
        self.chpwd_email = v
        self.chpwd_error = ""

    def set_chpwd_current(self, v: str):
        self.chpwd_current = v
        self.chpwd_error = ""

    def set_chpwd_new(self, v: str):
        self.chpwd_new = v
        self.chpwd_error = ""

    def set_chpwd_confirm(self, v: str):
        self.chpwd_confirm = v
        self.chpwd_error = ""

    def change_password(self):
        """Validate inputs and update Default Password in the Excel database."""
        result = change_admin_password(
            self.chpwd_email,
            self.chpwd_current,
            self.chpwd_new,
            self.chpwd_confirm,
        )
        if result["success"]:
            self.chpwd_error = ""
            self.chpwd_open = False
            self.chpwd_email = ""
            self.chpwd_current = ""
            self.chpwd_new = ""
            self.chpwd_confirm = ""
            return rx.toast.success(
                "Password updated successfully. Please sign in with your new password.",
                duration=5000,
            )
        else:
            self.chpwd_error = result["error"]

    async def facilitator_sign_in(self):
        """Facilitator sign in using Facilitator ID and password created by Admin."""
        self.facilitator_signin_error = ""
        self.facilitator_access_denied = False

        fid = self.facilitator_signin_id.strip()
        pwd = self.facilitator_signin_password.strip()

        if not fid:
            self.facilitator_signin_error = "Please enter your Facilitator ID."
            return
        if not pwd:
            self.facilitator_signin_error = "Please enter your password."
            return

        # Cross-state read: AdminState + shared list holds all facilitators
        admin_state = await self.get_state(AdminState)
        all_facilitators = list(SHARED_FACILITATORS)
        for f in admin_state.facilitators:
            if not any(sf["emp_id"].lower() == f["emp_id"].lower() for sf in all_facilitators):
                all_facilitators.append(f)

        match = next(
            (
                f for f in all_facilitators
                if f["emp_id"].lower() == fid.lower() or f["email"].lower() == fid.lower()
            ),
            None,
        )

        if match is None:
            self.facilitator_signin_error = "Facilitator ID not found. Please contact your administrator."
            return

        # Verify password against the password set by admin
        if match.get("password") and match["password"] != pwd:
            self.facilitator_signin_error = "Invalid password. Please try again."
            return

        self.is_facilitator_authenticated = True
        self.facilitator_name = match["name"]
        self.facilitator_email = match["email"]
        self.facilitator_emp_id = match["emp_id"]
        return rx.redirect("/facilitator/dashboard")

    def set_candidate_signin_id(self, value: str):
        self.candidate_signin_id = value

    def set_candidate_signin_password(self, value: str):
        self.candidate_signin_password = value

    async def candidate_sign_in(self):
        """Candidate login using Employee ID and password created by Admin."""
        self.candidate_signin_error = ""

        cid = self.candidate_signin_id.strip()
        pwd = self.candidate_signin_password.strip()

        if not cid:
            self.candidate_signin_error = "Please enter your Employee ID."
            return
        if not pwd:
            self.candidate_signin_error = "Please enter your password."
            return

        cid_lower = cid.lower()

        # --- Step 1: Search SHARED_CANDIDATES (plain Python list, no Reflex wrapping) ---
        # These are always correct plain dicts. Password comparison is safe here.
        match = None
        for c in SHARED_CANDIDATES:
            if c["emp_id"].lower() == cid_lower or c.get("email", "").lower() == cid_lower:
                match = c
                break

        # --- Step 2: If not in shared list, check admin_state for newly added candidates ---
        if match is None:
            admin_state = await self.get_state(AdminState)
            for c in admin_state.candidates:
                # Use plain string conversion to avoid Reflex Var comparison issues
                emp_id = str(c.get("emp_id", "")).lower()
                email = str(c.get("email", "")).lower()
                if emp_id == cid_lower or email == cid_lower:
                    # Re-construct as a plain dict to avoid Var wrapping
                    match = {
                        "emp_id": str(c.get("emp_id", "")),
                        "name": str(c.get("name", "")),
                        "email": str(c.get("email", "")),
                        "password": str(c.get("password", "")),
                    }
                    break

        if match is None:
            self.candidate_signin_error = (
                "Employee ID not found. "
                "Please check your ID or contact your administrator."
            )
            return

        # --- Step 3: Password check (plain string comparison) ---
        stored_pwd = str(match.get("password", ""))
        if stored_pwd and stored_pwd != pwd:
            self.candidate_signin_error = "Incorrect password. Please try again."
            return

        # --- Step 4: Success ---
        self.is_candidate_authenticated = True
        self.candidate_name = str(match.get("name", ""))
        self.candidate_email = str(match.get("email", ""))
        self.candidate_emp_id = str(match.get("emp_id", ""))

        try:
            from ai_hybrid_evaluator.state.candidate_state import CandidateProfileState
            profile = await self.get_state(CandidateProfileState)
            profile.full_name = self.candidate_name
            profile.email = self.candidate_email
            profile.emp_id = self.candidate_emp_id
        except Exception:
            pass

        return rx.redirect("/candidate/dashboard")

    def candidate_logout(self):
        self.is_candidate_authenticated = False
        self.candidate_name = ""
        self.candidate_email = ""
        self.candidate_emp_id = ""
        self.candidate_signin_id = ""
        self.candidate_signin_password = ""
        self.candidate_signin_error = ""
        return rx.redirect("/candidate/login")

    def facilitator_logout(self):
        self.is_facilitator_authenticated = False
        self.facilitator_name = ""
        self.facilitator_email = ""
        self.facilitator_emp_id = ""
        self.facilitator_signin_id = ""
        self.facilitator_signin_password = ""
        self.facilitator_signin_email = ""
        self.facilitator_signin_error = ""
        return rx.redirect("/facilitator/signin")