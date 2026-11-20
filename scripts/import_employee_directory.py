"""Run from the main project: python -m scripts.import_employee_directory WORKBOOK."""
import argparse
import json

from backend.database.mysql_json_store import active_mysql_store
from backend.services.employee_directory_service import import_employee_directory


def main():
    parser = argparse.ArgumentParser(description="Validate or import employee records into active MySQL storage.")
    parser.add_argument("workbook")
    parser.add_argument("--database", required=True, help="Expected active database name.")
    parser.add_argument("--apply", action="store_true", help="Import after validation. Default is read-only.")
    args = parser.parse_args()
    store = active_mysql_store()
    if store is None or store.configuration.get("database") != args.database:
        parser.error("The expected MySQL database is not active; no import performed.")
    result = import_employee_directory(args.workbook, dry_run=not args.apply)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
