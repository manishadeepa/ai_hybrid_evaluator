"""
Mock authentication API.

Simulates backend responses so the frontend can be built and tested
independently. The backend developer will replace the INSIDE of these
two functions with real API calls — the function names, arguments, and
return shape ({"success": bool, "error": str}) should stay the same so
nothing else in the app needs to change later.
"""

import os
import re
import pandas as pd

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def find_admin_excel_path() -> str | None:
    """Locate the admin_database.xlsx file in the project's data folder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        os.path.join(base_dir, "..", "data"),
        os.path.join(base_dir, "..", "data", "admin_database"),
        os.path.join(base_dir, "data"),
        os.path.join(os.getcwd(), "ai_hybrid_evaluator", "data"),
        os.path.join(os.getcwd(), "ai_hybrid_evaluator", "data", "admin_database"),
        os.path.join(os.getcwd(), "data"),
        os.path.join(os.getcwd(), "data", "admin_database"),
    ]
    for d in search_dirs:
        if os.path.isdir(d):
            direct = os.path.join(d, "admin_database.xlsx")
            if os.path.isfile(direct):
                return direct
            for fname in os.listdir(d):
                if fname.lower().endswith(".xlsx") and not fname.startswith("~$"):
                    return os.path.join(d, fname)
    return None


def mock_login(email: str, password: str) -> dict:
    """
    Authenticate Admin against the Excel database in the project's data folder.
    Matches EmployeeMail (case-insensitive) and Default Password (exact).
    """
    clean_email = (email or "").strip()
    clean_password = (password or "").strip()

    if not clean_email or not clean_password:
        return {"success": False, "error": "Invalid Admin email or password."}

    excel_path = find_admin_excel_path()
    if not excel_path or not os.path.isfile(excel_path):
        return {
            "success": False,
            "error": "Admin database file could not be found in the data folder.",
        }

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Unable to read Admin database: {str(e)}",
        }

    col_map = {str(c).strip().lower(): c for c in df.columns}
    mail_col = col_map.get("employeemail")
    pwd_col = col_map.get("default password") or col_map.get("password")
    id_col = col_map.get("employeeid")
    name_col = col_map.get("employeename")

    if not mail_col or not pwd_col:
        return {
            "success": False,
            "error": "Admin database is missing required columns (EmployeeMail, Default Password).",
        }

    target_email = clean_email.lower()

    for _, row in df.iterrows():
        row_email = str(row[mail_col]).strip().lower() if pd.notna(row[mail_col]) else ""
        row_pwd = str(row[pwd_col]).strip() if pd.notna(row[pwd_col]) else ""

        if row_email == target_email and row_pwd == clean_password:
            emp_id = str(row[id_col]).strip() if id_col and pd.notna(row[id_col]) else ""
            emp_name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
            emp_mail = str(row[mail_col]).strip() if pd.notna(row[mail_col]) else ""
            return {
                "success": True,
                "error": "",
                "employee_id": emp_id,
                "employee_name": emp_name or "Admin",
                "employee_mail": emp_mail,
            }

    return {"success": False, "error": "Invalid Admin email or password."}


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


def change_admin_password(email: str, current_password: str, new_password: str, confirm_password: str) -> dict:
    """
    Change an Admin's password in the Excel database.
    - Finds the employee by EmployeeMail (case-insensitive).
    - Verifies current_password matches the stored Default Password.
    - Validates new_password == confirm_password.
    - Writes the new password back to the Excel file.
    - Returns {"success": bool, "error": str}.
    """
    clean_email = (email or "").strip()
    clean_current = (current_password or "").strip()
    clean_new = (new_password or "").strip()
    clean_confirm = (confirm_password or "").strip()

    if not clean_email or not clean_current or not clean_new or not clean_confirm:
        return {"success": False, "error": "Please fill in all fields."}

    if clean_new != clean_confirm:
        return {"success": False, "error": "New passwords do not match."}

    if clean_new == clean_current:
        return {"success": False, "error": "New password must be different from the current password."}

    excel_path = find_admin_excel_path()
    if not excel_path or not os.path.isfile(excel_path):
        return {
            "success": False,
            "error": "Admin database file could not be found in the data folder.",
        }

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        return {"success": False, "error": f"Unable to read Admin database: {str(e)}"}

    col_map = {str(c).strip().lower(): c for c in df.columns}
    mail_col = col_map.get("employeemail")
    pwd_col = col_map.get("default password") or col_map.get("password")

    if not mail_col or not pwd_col:
        return {
            "success": False,
            "error": "Admin database is missing required columns.",
        }

    target_email = clean_email.lower()
    matched_idx = None

    for idx, row in df.iterrows():
        row_email = str(row[mail_col]).strip().lower() if pd.notna(row[mail_col]) else ""
        if row_email == target_email:
            matched_idx = idx
            row_pwd = str(row[pwd_col]).strip() if pd.notna(row[pwd_col]) else ""
            if row_pwd != clean_current:
                return {"success": False, "error": "Current password is incorrect."}
            break

    if matched_idx is None:
        return {"success": False, "error": "No Admin account found with that email address."}

    # Update only the Default Password for that row
    df.at[matched_idx, pwd_col] = clean_new

    try:
        df.to_excel(excel_path, index=False)
    except Exception as e:
        return {"success": False, "error": f"Failed to save updated password: {str(e)}"}

    return {"success": True, "error": ""}