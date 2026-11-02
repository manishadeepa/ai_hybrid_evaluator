"""Authentication helpers used by the Admin sign-in and password forms."""

import re

from backend.services.group_admin_service import GroupAdminService
from backend.services.master_admin_service import MasterAdminService

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def mock_login(username: str, password: str) -> dict:
    """Authenticate against the persistent Master Admin or Group Admin stores."""
    clean_username = (username or "").strip()
    clean_password = (password or "").strip()

    if not clean_username or not clean_password:
        return {"success": False, "error": "Invalid Admin username or password."}

    try:
        master_admin = MasterAdminService().authenticate(clean_username, clean_password)
        if master_admin:
            return {
                "success": True,
                "error": "",
                "employee_id": "",
                "employee_name": master_admin["username"],
                "employee_mail": master_admin["username"],
                "role": "Master Admin",
            }

        group_admin = GroupAdminService().authenticate(clean_username, clean_password)
    except (OSError, ValueError):
        return {
            "success": False,
            "error": "Unable to load administrator accounts. Please contact your administrator.",
        }

    if group_admin:
        return {
            "success": True,
            "error": "",
            "employee_id": group_admin.get("employee_id", ""),
            "employee_name": group_admin["username"],
            "employee_mail": group_admin["username"],
            "role": "Group Admin",
        }
    return {"success": False, "error": "Invalid Admin username or password."}


def mock_signup(username: str, employee_id: str, email: str, password: str, confirm_password: str) -> dict:
    """Simulates POST /api/auth/signup"""
    if not all([username, employee_id, email, password, confirm_password]):
        return {"success": False, "error": "Please fill in all fields."}
    if not re.match(EMAIL_REGEX, email):
        return {"success": False, "error": "Enter a valid email address."}
    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters."}
    if password != confirm_password:
        return {"success": False, "error": "Passwords do not match."}
    return {"success": True, "error": ""}


def change_admin_password(username: str, current_password: str, new_password: str, confirm_password: str) -> dict:
    """Change a stored admin password after verifying the current password."""
    clean_username = (username or "").strip()
    clean_current = (current_password or "").strip()
    clean_new = (new_password or "").strip()
    clean_confirm = (confirm_password or "").strip()

    if not clean_username or not clean_current or not clean_new or not clean_confirm:
        return {"success": False, "error": "Please fill in all fields."}

    if clean_new != clean_confirm:
        return {"success": False, "error": "New passwords do not match."}

    if clean_new == clean_current:
        return {"success": False, "error": "New password must be different from the current password."}

    try:
        master_admin_service = MasterAdminService()
        master_admin = master_admin_service.authenticate(clean_username, clean_current)
        if master_admin:
            master_admin_service.update(
                master_admin["username"], master_admin["username"], clean_new
            )
            return {"success": True, "error": ""}

        group_admin_service = GroupAdminService()
        group_admin = group_admin_service.authenticate(clean_username, clean_current)
        if group_admin:
            group_admin_service.update(
                group_admin["username"], group_admin["username"], clean_new
            )
            return {"success": True, "error": ""}
    except (OSError, ValueError):
        return {
            "success": False,
            "error": "Unable to update the administrator password. Please try again.",
        }

    return {"success": False, "error": "Current password is incorrect."}