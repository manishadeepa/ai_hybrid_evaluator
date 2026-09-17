import json
from pathlib import Path
from typing import Any


class JSONRepository:
    """Reusable JSON file storage for backend repositories."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create the parent directory and an empty JSON list if needed."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            self._write_data([])

    def _read_data(self) -> list[dict[str, Any]]:
        """Read and return records from the JSON file."""
        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(
                f"JSON repository must contain a list: {self.file_path}"
            )

        return data

    def _write_data(self, data: list[dict[str, Any]]) -> None:
        """Write records to the JSON file."""
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def get_all(self) -> list[dict[str, Any]]:
        """Return all stored records."""
        return self._read_data()

    def save_all(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace all stored records."""
        self._write_data(data)
        return data
