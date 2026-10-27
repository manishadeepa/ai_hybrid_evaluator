import unittest
from unittest.mock import patch

import reflex as rx

from ai_hybrid_evaluator.state.admin_state import AdminState


class AdminCandidateEmployeeLookupTests(unittest.IsolatedAsyncioTestCase):
    async def get_admin_state(self):
        root = rx.State(_reflex_internal_init=True)
        return await root.get_state(AdminState)

    async def test_employee_lookup_fills_form_without_changing_password(self):
        admin = await self.get_admin_state()
        admin.new_candidate_password = "secret123"
        with patch(
            "ai_hybrid_evaluator.state.admin_state.find_employee_by_id",
            return_value={
                "name": "Ada Example",
                "email": "ada@example.com",
                "department": "Engineering",
            },
        ):
            admin.set_new_candidate_id("E001")

        self.assertEqual(admin.new_candidate_name, "Ada Example")
        self.assertEqual(admin.new_candidate_email, "ada@example.com")
        self.assertEqual(admin.new_candidate_department, "Engineering")
        self.assertEqual(admin.new_candidate_password, "secret123")
        self.assertEqual(admin.candidate_form_error, "")

    async def test_missing_employee_id_clears_directory_fields_and_reports_error(self):
        admin = await self.get_admin_state()
        admin.new_candidate_name = "Stale name"
        admin.new_candidate_email = "stale@example.com"
        admin.new_candidate_department = "Stale department"
        with patch(
            "ai_hybrid_evaluator.state.admin_state.find_employee_by_id",
            return_value=None,
        ):
            admin.set_new_candidate_id("E999")

        self.assertEqual(admin.new_candidate_name, "")
        self.assertEqual(admin.new_candidate_email, "")
        self.assertEqual(admin.new_candidate_department, "")
        self.assertEqual(admin.candidate_form_error, "Employee ID was not found.")
