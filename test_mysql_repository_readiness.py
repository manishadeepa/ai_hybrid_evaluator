"""Regression tests for empty MySQL collections and scoped reads without files."""
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from backend.database.mysql_json_store import MySQLJSONStore
from backend.repositories import json_repository as routing
from backend.repositories.json_repository import JSONRepository, repository_read_scope


@pytest.fixture
def mysql_route(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'contract.sqlite'}")
    store = MySQLJSONStore({}, engine=engine)
    def route(path):
        return Path(path), store, Path(path).name
    try:
        with patch.object(routing, "_mysql_target", side_effect=route):
            yield tmp_path, store
    finally:
        engine.dispose()


def test_missing_mysql_collection_is_empty_without_creating_local_file(mysql_route):
    root, store = mysql_route
    repository = JSONRepository(root / "items.json")
    assert repository.get_all() == []
    assert not store.has_document("items.json")
    assert not (root / "items.json").exists()


def test_scoped_mysql_reads_follow_writes_without_files(mysql_route):
    root, store = mysql_route
    repository = JSONRepository(root / "items.json")
    with repository_read_scope():
        assert repository.get_all() == []
        repository.save_all([{"id": "one"}])
        assert repository.get_all() == [{"id": "one"}]
        store.save_document("items.json", [{"id": "two"}])
        assert repository.get_all() == [{"id": "two"}]
    assert not (root / "items.json").exists()


@pytest.mark.parametrize("invalid", [{}, "invalid", ["invalid"], None])
def test_existing_invalid_mysql_payload_is_not_treated_as_empty(mysql_route, invalid):
    root, store = mysql_route
    store.save_document("items.json", invalid)
    with pytest.raises(ValueError, match="Invalid MySQL application data"):
        JSONRepository(root / "items.json").get_all()
