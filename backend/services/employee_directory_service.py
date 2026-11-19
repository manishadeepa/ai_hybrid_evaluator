from pathlib import Path

import pandas as pd


EMPLOYEE_WORKBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "EMP_information.xlsx"
)


def list_directory_employees() -> list[dict[str, str]]:
    """Read public employee details from the project-local workbook."""

    if not EMPLOYEE_WORKBOOK_PATH.is_file():
        raise FileNotFoundError(
            f"Employee information workbook was not found at {EMPLOYEE_WORKBOOK_PATH}."
        )

    employees = pd.read_excel(
        EMPLOYEE_WORKBOOK_PATH,
        sheet_name="Sheet1",
        dtype=str,
    )
    columns = {
        " ".join(str(column).split()).casefold(): column
        for column in employees.columns
    }
    required_columns = {"employee id", "name", "email id", "department"}
    missing_columns = sorted(required_columns - columns.keys())
    if missing_columns:
        raise ValueError(
            "Employee information workbook is missing required columns: "
            + ", ".join(missing_columns)
        )

    records = []
    for _, employee in employees.iterrows():
        def cell_text(column_name: str) -> str:
            value = employee[columns[column_name]]
            return "" if pd.isna(value) else str(value).strip()

        employee_id = cell_text("employee id")
        if employee_id:
            records.append({
                "emp_id": employee_id,
                "name": cell_text("name"),
                "email": cell_text("email id"),
                "department": cell_text("department"),
            })
    return records


def find_employee_by_id(employee_id: str) -> dict[str, str] | None:
    """Return one employee's public form details by exact Employee ID."""
    if not employee_id:
        return None
    for employee in list_directory_employees():
        if employee["emp_id"] == employee_id:
            return {key: employee[key] for key in ("name", "email", "department")}
    return None
