from copy import deepcopy
from pathlib import Path

from backend.repositories.json_repository import JSONRepository


class FacilitatorRepository:
    """Persist facilitator accounts using the backend JSON repository."""

    def __init__(self, file_path=None):
        use_default_path = file_path is None
        self.file_path = (
            Path(file_path)
            if file_path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "facilitators.json"
        )

        # Bootstrap only the default store, and only when it does not exist.
        # This preserves the existing seeded accounts on first startup.
        should_bootstrap = use_default_path and not self.file_path.exists()
        self.storage = JSONRepository(self.file_path)

        if should_bootstrap:
            from ai_hybrid_evaluator.models.models import SHARED_FACILITATORS

            initial_records = [dict(row) for row in SHARED_FACILITATORS]
            self._validate(initial_records)
            self.storage.save_all(deepcopy(initial_records))

    @staticmethod
    def _validate(records):
        if not isinstance(records, list):
            raise ValueError("Facilitator records must be a list.")

        employee_ids = []

        for row in records:
            if not isinstance(row, dict):
                raise ValueError("Each facilitator record must be an object.")

            for field in ("emp_id", "name", "email", "password"):
                if not isinstance(row.get(field), str):
                    raise ValueError(
                        f"Facilitator field '{field}' must be a string."
                    )

            if not row["emp_id"].strip() or not row["name"].strip() or not row["email"].strip():
                raise ValueError(
                    "Facilitator employee ID, name, and email cannot be empty."
                )

            if not isinstance(row.get("phone", ""), str):
                raise ValueError("Facilitator phone must be a string.")

            employee_ids.append(row["emp_id"].strip().casefold())

        if len(employee_ids) != len(set(employee_ids)):
            raise ValueError("Duplicate facilitator employee ID.")

    def get_all(self):
        records = self.storage.get_all()
        self._validate(records)
        return deepcopy(records)

    def get_by_id(self, emp_id):
        target = str(emp_id).strip().casefold()
        return next(
            (
                row
                for row in self.get_all()
                if row["emp_id"].strip().casefold() == target
            ),
            None,
        )

    def save_all(self, records):
        # Validate the current file before replacing it, so malformed data
        # is never silently overwritten.
        self.get_all()
        self._validate(records)
        return self.storage.save_all(deepcopy(records))

    def save(self, facilitator):
        records = self.get_all()
        new_id = str(facilitator.get("emp_id", "")).strip().casefold()

        if any(row["emp_id"].strip().casefold() == new_id for row in records):
            raise ValueError("This facilitator employee ID already exists.")

        updated = deepcopy(facilitator)
        records.append(updated)
        self.save_all(records)
        return deepcopy(updated)

    def replace(self, old_emp_id, facilitator):
        records = self.get_all()
        old_id = str(old_emp_id).strip().casefold()

        index = next(
            (
                i
                for i, row in enumerate(records)
                if row["emp_id"].strip().casefold() == old_id
            ),
            None,
        )

        if index is None:
            raise ValueError("Facilitator was not found.")

        updated = deepcopy(facilitator)
        records[index] = updated
        self.save_all(records)
        return deepcopy(updated)

    def delete(self, emp_id):
        target = str(emp_id).strip().casefold()
        records = self.get_all()
        remaining = [
            row
            for row in records
            if row["emp_id"].strip().casefold() != target
        ]
        self.save_all(remaining)