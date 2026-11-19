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
        ), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
            await admin.set_new_candidate_id("E001")

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
        ), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
            await admin.set_new_candidate_id("E999")

        self.assertEqual(admin.new_candidate_name, "")
        self.assertEqual(admin.new_candidate_email, "")
        self.assertEqual(admin.new_candidate_department, "")
        self.assertEqual(admin.candidate_form_error, "Employee ID was not found.")

    async def test_workbook_name_or_id_search_populates_all_fields(self):
        for query in ("Ada Example", "EMP1", "ada example"):
            admin = await self.get_admin_state()
            admin.new_candidate_password = "unchanged"
            with patch("ai_hybrid_evaluator.state.admin_state.list_directory_employees", return_value=[
                {"emp_id": "EMP1", "name": "Ada Example", "email": "ada@example.com", "department": "Engineering"}
            ]), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
                await admin.set_employee_search_query(query)
            self.assertEqual(admin.new_candidate_id, "EMP1")
            self.assertEqual(admin.new_candidate_name, "Ada Example")
            self.assertEqual(admin.new_candidate_email, "ada@example.com")
            self.assertEqual(admin.new_candidate_department, "Engineering")
            self.assertEqual(admin.new_candidate_password, "unchanged")

    async def test_duplicate_names_require_selection(self):
        admin = await self.get_admin_state()
        with patch("ai_hybrid_evaluator.state.admin_state.list_directory_employees", return_value=[
            {"emp_id": "EMP1", "name": "Ada Example", "email": "one@example.com", "department": "Engineering"},
            {"emp_id": "EMP2", "name": "Ada Example", "email": "two@example.com", "department": "Engineering"}
        ]), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
            await admin.set_employee_search_query("Ada Example")
            self.assertFalse(admin.employee_selected)
            self.assertEqual(len(admin.filtered_employee_suggestions), 2)
            await admin.select_employee_suggestion_by_id("EMP2")
            self.assertEqual(admin.new_candidate_email, "two@example.com")

    async def test_missing_workbook_reports_error(self):
        admin = await self.get_admin_state()
        with patch("ai_hybrid_evaluator.state.admin_state.list_directory_employees", side_effect=FileNotFoundError("Workbook missing")), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
            await admin.set_employee_search_query("EMP1")
        self.assertIn("Workbook missing", admin.candidate_form_error)
        self.assertEqual(admin.workbook_directory_employees, [])

    async def test_name_field_uses_workbook_lookup(self):
        admin = await self.get_admin_state()
        with patch("ai_hybrid_evaluator.state.admin_state.list_directory_employees", return_value=[
            {"emp_id": "EMP1", "name": "Ada Example", "email": "ada@example.com", "department": "Engineering"}
        ]), patch("ai_hybrid_evaluator.state.admin_state.has_admin_session", return_value=True):
            await admin.set_new_candidate_name("Ada Example")
        self.assertEqual(admin.new_candidate_id, "EMP1")
        self.assertEqual(admin.new_candidate_email, "ada@example.com")
