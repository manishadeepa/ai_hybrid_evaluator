"""
Mock authentication API.

Simulates backend responses so the frontend can be built and tested
independently. The backend developer will replace the INSIDE of these
two functions with real API calls — the function names, arguments, and
return shape ({"success": bool, "error": str}) should stay the same so
nothing else in the app needs to change later.
"""

import re

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# Temporary mock account — remove once real auth is connected.
MOCK_ADMIN_ACCOUNT = {
    "email": "admin@genaievaluator.com",
    "password": "Admin@123",
}


def mock_login(email: str, password: str) -> dict:
    """Simulates POST /api/auth/login"""
    if not email or not password:
        return {"success": False, "error": "Please fill in all fields."}
    if not re.match(EMAIL_REGEX, email):
        return {"success": False, "error": "Enter a valid email address."}
    if email == MOCK_ADMIN_ACCOUNT["email"] and password == MOCK_ADMIN_ACCOUNT["password"]:
        return {"success": True, "error": ""}
    return {"success": False, "error": "Invalid email or password."}


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