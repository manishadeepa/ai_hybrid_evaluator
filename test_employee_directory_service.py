import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.services import employee_directory_service


class EmployeeDirectoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workbook = Path(self.temp.name) / "EMP_information.xlsx"
        self.workbook.touch()
        storage_patch = patch.object(employee_directory_service, "read_json_document", return_value=None)
        mysql_patch = patch("backend.database.mysql_json_store.active_mysql_store", return_value=None)
        storage_patch.start()
        mysql_patch.start()
        self.addCleanup(storage_patch.stop)
        self.addCleanup(mysql_patch.stop)

    @patch("backend.services.employee_directory_service.pd.read_excel")
    def test_normalizes_header_whitespace_and_returns_employee_details(self, read_excel):
        read_excel.return_value = pd.DataFrame(
            [
                {
                    "Employee ID": "E001",
                    "Name": "  Ada Example ",
                    "Email ID ": " ada@example.com ",
                    "Department": " Engineering ",
                }
            ]
        )
        with patch.object(employee_directory_service, "EMPLOYEE_WORKBOOK_PATH", self.workbook):
            employee = employee_directory_service.find_employee_by_id("E001")

        self.assertEqual(
            employee,
            {
                "name": "Ada Example",
                "email": "ada@example.com",
                "department": "Engineering",
            },
        )
        read_excel.assert_called_once_with(
            self.workbook,
            sheet_name="Sheet1",
            dtype=str,
            keep_default_na=False,
        )

    @patch("backend.services.employee_directory_service.pd.read_excel")
    def test_employee_id_matching_is_exact(self, read_excel):
        read_excel.return_value = pd.DataFrame(
            [
                {
                    "Employee ID": "E001",
                    "Name": "Ada Example",
                    "Email ID": "ada@example.com",
                    "Department": "Engineering",
                }
            ]
        )
        with patch.object(employee_directory_service, "EMPLOYEE_WORKBOOK_PATH", self.workbook):
            self.assertIsNone(employee_directory_service.find_employee_by_id("E00"))
            self.assertIsNone(employee_directory_service.find_employee_by_id("e001"))
            self.assertIsNone(employee_directory_service.find_employee_by_id("E002"))
