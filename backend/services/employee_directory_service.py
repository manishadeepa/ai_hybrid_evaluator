"""Employee directory routed through the application's active JSON/MySQL storage."""
from pathlib import Path

import pandas as pd

from backend.data_paths import DEFAULT_DATA_DIR
from backend.repositories.json_repository import read_json_document


EMPLOYEE_WORKBOOK_PATH = Path(__file__).resolve().parents[1] / "data" / "EMP_information.xlsx"
EMPLOYEE_DOCUMENT = "employee_directory.json"


def _validate_records(records):
    if not isinstance(records, list):
        raise ValueError("Employee directory must contain a list of records.")
    normalized = []
    seen = set()
    for row_number, record in enumerate(records, start=2):
        if not isinstance(record, dict):
            raise ValueError(f"Employee directory row {row_number} is invalid.")
        row = {}
        for field in ("emp_id", "name", "email", "department"):
            value = record.get(field)
            if not isinstance(value, str):
                raise ValueError(f"Employee directory row {row_number} has an invalid {field}.")
            row[field] = value.strip()
        if not row["emp_id"]:
            raise ValueError(f"Employee directory row {row_number} has no employee ID.")
        identity = row["emp_id"].casefold()
        if identity in seen:
            raise ValueError(f"Employee directory row {row_number} has a duplicate employee ID.")
        seen.add(identity)
        normalized.append(row)
    return normalized


def read_employee_workbook(workbook_path: str | Path) -> list[dict[str, str]]:
    """Validate workbook rows without modifying the source or persistence."""
    path = Path(workbook_path)
    if not path.is_file():
        raise FileNotFoundError(f"Employee information workbook was not found at {path}.")
    employees = pd.read_excel(path, sheet_name="Sheet1", dtype=str, keep_default_na=False)
    columns = {}
    for column in employees.columns:
        key = " ".join(str(column).split()).casefold()
        if key in columns:
            raise ValueError("Employee workbook contains duplicate column headings.")
        columns[key] = column
    required = {"employee id", "name", "email id", "department"}
    missing = sorted(required - columns.keys())
    if missing:
        raise ValueError("Employee information workbook is missing required columns: " + ", ".join(missing))
    records = []
    for _, employee in employees.iterrows():
        def text(key):
            value = employee[columns[key]]
            return "" if pd.isna(value) else str(value).strip()
        row = dict(zip(("emp_id", "name", "email", "department"),
                       (text("employee id"), text("name"), text("email id"), text("department"))))
        if any(row.values()):
            records.append(row)
    return _validate_records(records)


def list_directory_employees() -> list[dict[str, str]]:
    """Read shared storage; workbook compatibility is limited to folder mode."""
    records = read_json_document(DEFAULT_DATA_DIR / EMPLOYEE_DOCUMENT, default=None)
    if records is not None:
        return _validate_records(records)
    from backend.database.mysql_json_store import active_mysql_store
    if active_mysql_store() is not None:
        raise ValueError("The employee directory has not been imported into active MySQL storage.")
    path = EMPLOYEE_WORKBOOK_PATH
    # Preserve the older project's Desktop workbook location in folder mode only.
    if not path.is_file() and path == Path(__file__).resolve().parents[1] / "data" / "EMP_information.xlsx":
        legacy = Path.home() / "OneDrive" / "Desktop" / "EMP_information.xlsx"
        if legacy.is_file():
            path = legacy
    return read_employee_workbook(path)


def find_employee_by_id(employee_id: str) -> dict[str, str] | None:
    """Preserve exact ID matching and the existing public response fields."""
    if not employee_id:
        return None
    for employee in list_directory_employees():
        if employee["emp_id"] == employee_id:
            return {key: employee[key] for key in ("name", "email", "department")}
    return None


def import_employee_directory(workbook_path: str | Path, *, dry_run=True) -> dict:
    """Explicit MySQL import: validate first, refuse conflicting existing data."""
    records = read_employee_workbook(workbook_path)
    if not records:
        raise ValueError("No employee records were found; import was not started.")
    from backend.database.mysql_json_store import active_mysql_store
    from backend.services.assessment_service import _PERSISTENCE_LOCK
    with _PERSISTENCE_LOCK:
        store = active_mysql_store()
        if store is None:
            raise ValueError("MySQL must already be active; employee import will not activate or switch storage.")
        exists = store.has_document(EMPLOYEE_DOCUMENT)
        if exists and store.get_document(EMPLOYEE_DOCUMENT) != records:
            raise ValueError("MySQL contains different employee data; nothing was overwritten.")
        if not dry_run and not exists:
            store.import_documents([(EMPLOYEE_DOCUMENT, records)])
        if not dry_run and store.get_document(EMPLOYEE_DOCUMENT) != records:
            raise ValueError("Employee import read-back verification failed.")
    return {"records": len(records), "document": EMPLOYEE_DOCUMENT,
            "status": "validated" if dry_run else ("already_present" if exists else "imported")}
