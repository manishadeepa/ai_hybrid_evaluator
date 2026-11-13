import json

import pytest
from sqlalchemy import create_engine

from backend.database.mysql_json_store import MySQLJSONStore
from backend.repositories.json_repository import (
    JSONRepository,
    json_document_exists,
    read_json_document,
    write_json_document,
)
import backend.database.mysql_json_store as mysql_store_module
import backend.repositories.json_repository as json_repository_module


@pytest.fixture
def mysql_store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'storage-test.sqlite'}")
    store = MySQLJSONStore({}, engine=engine)
    yield store
    engine.dispose()


def test_mysql_document_store_persists_and_preserves_existing_data(mysql_store):
    expected = [{"candidate_id": "EMP1", "name": "Demo Candidate"}]
    mysql_store.save_document("candidates.json", expected)

    assert mysql_store.get_document("candidates.json") == expected

    mysql_store.import_documents([("candidates.json", [])])
    assert mysql_store.get_document("candidates.json") == expected

    with pytest.raises(ValueError, match="different data"):
        mysql_store.import_documents(
            [("candidates.json", [{"candidate_id": "EMP2"}])]
        )
    assert mysql_store.get_document("candidates.json") == expected


def test_json_repository_routes_to_active_mysql_store(tmp_path, mysql_store, monkeypatch):
    path = tmp_path / "candidates.json"
    monkeypatch.setattr(
        mysql_store_module,
        "active_mysql_store",
        lambda: mysql_store,
    )
    monkeypatch.setattr(
        json_repository_module,
        "get_active_data_dir",
        lambda: tmp_path,
    )
    repository = JSONRepository(path)
    rows = [{"candidate_id": "EMP2", "name": "Other Candidate"}]

    repository.save_all(rows)

    assert repository.get_all() == rows
    assert not path.exists()
    assert mysql_store.get_document("candidates.json") == rows


def test_document_payload_is_valid_json(mysql_store):
    payload = [{"id": "assessment-1", "tests": ["Test 1"]}]
    mysql_store.save_document("assessments.json", payload)
    fetched = mysql_store.get_document("assessments.json")
    assert json.loads(json.dumps(fetched)) == payload


def test_arbitrary_json_documents_route_to_mysql(tmp_path, mysql_store, monkeypatch):
    path = tmp_path / "assessment_weightages.json"
    expected = {"Assessment 1": {"Test 1": 100}}
    monkeypatch.setattr(
        mysql_store_module,
        "active_mysql_store",
        lambda: mysql_store,
    )
    monkeypatch.setattr(
        json_repository_module,
        "get_active_data_dir",
        lambda: tmp_path,
    )

    write_json_document(path, expected)

    assert read_json_document(path, {}) == expected
    assert json_document_exists(path)
    assert mysql_store.get_document("assessment_weightages.json") == expected
    assert not path.exists()
