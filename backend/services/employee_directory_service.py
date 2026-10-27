from pathlib import Path

import pandas as pd


EMPLOYEE_WORKBOOK_PATH = (
    Path.home() / "OneDrive" / "Desktop" / "EMP_information.xlsx"
)


def find_employee_by_id(employee_id: str) -> dict[str, str] | None:
    """Return one employee's public form details from the local directory."""
    if not employee_id:
        return None

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

    employee_id_column = columns["employee id"]
    matches = employees.loc[employees[employee_id_column] == employee_id]
    if matches.empty:
        return None

    employee = matches.iloc[0]

    def cell_text(column_name: str) -> str:
        value = employee[columns[column_name]]
        return "" if pd.isna(value) else str(value).strip()

    return {
        "name": cell_text("name"),
        "email": cell_text("email id"),
        "department": cell_text("department"),
    }
