from pathlib import Path
from unittest.mock import Mock, patch
import importlib.util
import os

import pandas as pd
import pytest
from sqlalchemy import create_engine
from backend.database.mysql_json_store import MySQLJSONStore

from backend.services import employee_directory_service as service
ROWS = [{"emp_id": "E001", "name": "Ada", "email": "ada@example.test", "department": "Engineering"}]


def test_shared_lookup_never_reads_workbook():
    with patch.object(service, "read_json_document", return_value=ROWS), patch.object(service.pd, "read_excel", side_effect=AssertionError("local workbook accessed")):
        assert service.list_directory_employees() == ROWS
        assert service.find_employee_by_id("E001") == {key: ROWS[0][key] for key in ("name", "email", "department")}
        assert service.find_employee_by_id("e001") is None
        assert service.find_employee_by_id("") is None


def test_missing_mysql_directory_fails_closed():
    with patch.object(service, "read_json_document", return_value=None), patch("backend.database.mysql_json_store.active_mysql_store", return_value=Mock()), patch.object(service, "read_employee_workbook", side_effect=AssertionError("fallback")):
        with pytest.raises(ValueError, match="not been imported"):
            service.list_directory_employees()


def test_empty_shared_directory_does_not_fallback():
    with patch.object(service, "read_json_document", return_value=[]):
        assert service.list_directory_employees() == []


@pytest.mark.parametrize("records", [None, {}, [None], [dict(ROWS[0], emp_id="")], ROWS + [dict(ROWS[0], emp_id="e001")]])
def test_invalid_shared_records_rejected(records):
    with pytest.raises(ValueError):
        service._validate_records(records)


def test_workbook_headers_whitespace_and_leading_zero_ids(tmp_path):
    book = tmp_path / "input.xlsx"
    book.touch()
    frame = pd.DataFrame([{"Employee ID": "001", "Name": " Ada ", "Email ID ": "NA", "Department": " Engineering "}])
    with patch.object(service.pd, "read_excel", return_value=frame):
        rows = service.read_employee_workbook(book)
    assert rows == [dict(ROWS[0], emp_id="001", email="NA")]


@pytest.mark.parametrize("ids", [["", "E1"], ["E1", "e1"]])
def test_workbook_missing_or_duplicate_id_rejected(tmp_path, ids):
    book = tmp_path / "input.xlsx"
    book.touch()
    frame = pd.DataFrame([{"Employee ID": identity, "Name": "Ada", "Email ID": "a@example.test", "Department": "Eng"} for identity in ids])
    with patch.object(service.pd, "read_excel", return_value=frame), pytest.raises(ValueError):
        service.read_employee_workbook(book)


def test_mysql_import_dry_run_idempotence_conflict_and_lookup(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'contract.sqlite'}")
    store = MySQLJSONStore({}, engine=engine)
    try:
        with patch.object(service, "read_employee_workbook", return_value=ROWS), patch("backend.database.mysql_json_store.active_mysql_store", return_value=store):
            assert service.import_employee_directory("unused")["status"] == "validated"
            assert not store.has_document(service.EMPLOYEE_DOCUMENT)
            assert service.import_employee_directory("unused", dry_run=False)["status"] == "imported"
            assert service.import_employee_directory("unused", dry_run=False)["status"] == "already_present"
            with patch.object(service, "read_json_document", side_effect=lambda path, default=None: store.get_document(Path(path).name, default)):
                assert service.list_directory_employees() == ROWS
            store.save_document(service.EMPLOYEE_DOCUMENT, [dict(ROWS[0], name="Changed")])
            with pytest.raises(ValueError, match="nothing was overwritten"):
                service.import_employee_directory("unused", dry_run=False)
            assert store.get_document(service.EMPLOYEE_DOCUMENT)[0]["name"] == "Changed"
    finally:
        engine.dispose()


def test_import_requires_active_mysql():
    with patch.object(service, "read_employee_workbook", return_value=ROWS), patch("backend.database.mysql_json_store.active_mysql_store", return_value=None):
        with pytest.raises(ValueError, match="must already be active"):
            service.import_employee_directory("unused", dry_run=False)
