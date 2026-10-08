from copy import deepcopy
from pathlib import Path

from backend.repositories.json_repository import JSONRepository


class AIConnectionRepository:
    def __init__(self, file_path=None):
        self.file_path = (
            Path(file_path)
            if file_path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "ai_connections.json"
        )

    def get_all(self):
        if not self.file_path.exists():
            return []

        rows = JSONRepository(self.file_path).get_all()

        ids = [row.get("connection_id") for row in rows]

        if any(
            not isinstance(value, str) or not value
            for value in ids
        ):
            raise ValueError("Invalid AI connection identity.")

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate AI connection identity.")

        if sum(bool(row.get("active")) for row in rows) > 1:
            raise ValueError(
                "More than one AI connection is active."
            )

        return deepcopy(rows)

    def get_active(self):
        return next(
            (
                row
                for row in self.get_all()
                if row.get("active")
            ),
            None,
        )

    def save_and_activate(self, record):
        rows = self.get_all()
        connection_id = record["connection_id"]

        name = record["name"].strip().casefold()

        if any(
            row["connection_id"] != connection_id
            and row.get("name", "").strip().casefold() == name
            for row in rows
        ):
            raise ValueError(
                "A connection with this name already exists."
            )

        updated = [
            {**row, "active": False}
            for row in rows
            if row["connection_id"] != connection_id
        ]

        saved = deepcopy(record)
        saved["active"] = True
        updated.append(saved)

        JSONRepository(self.file_path).save_all(updated)

        return deepcopy(saved)