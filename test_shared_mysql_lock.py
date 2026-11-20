"""Shared-lock contract tests; no live database or credentials required."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import OperationalError

from backend.database import mysql_unit_of_work as locking
from backend.document_updates import _merge, merge_session_document


def fake_store(results):
    connection = Mock(invalidated=False, closed=False)
    transaction = Mock(is_active=True)
    connection.begin.return_value = transaction
    connection.execute.side_effect = [Mock(scalar_one=Mock(return_value=value)) for value in results]
    engine = SimpleNamespace(dialect=SimpleNamespace(name="mysql"), url=SimpleNamespace(host="localhost", port=3306, database="app"), connect=Mock(return_value=connection))
    return SimpleNamespace(engine=engine, configuration={"database":"app"}, ensure_schema=Mock()), connection, transaction


@pytest.mark.parametrize("result", [0, None])
def test_timeout_or_null_never_enters_operation(result):
    store, connection, transaction = fake_store([result])
    entered = False
    with pytest.raises(ValueError, match="lock could not be acquired"):
        with locking.mysql_unit_of_work(store):
            entered = True
    assert not entered
    transaction.commit.assert_not_called()
    connection.close.assert_called_once()


def test_nested_operation_pins_connection_and_commits_once():
    store, connection, transaction = fake_store([1, 1, 1])
    with locking.mysql_unit_of_work(store) as outer:
        with locking.document_connection(store, write=True) as inner:
            assert inner is outer is connection
    store.engine.connect.assert_called_once()
    transaction.commit.assert_called_once()
    transaction.rollback.assert_not_called()
    statements = [str(call.args[0]) for call in connection.execute.call_args_list]
    assert "GET_LOCK" in statements[0]
    assert "IS_USED_LOCK" in statements[1]
    assert "RELEASE_LOCK" in statements[2]


def test_nested_caught_error_rolls_back_outer_operation():
    store, connection, transaction = fake_store([1, 1])
    with pytest.raises(ValueError, match="earlier failure"):
        with locking.mysql_unit_of_work(store):
            try:
                with locking.mysql_unit_of_work(store):
                    raise RuntimeError("test")
            except RuntimeError:
                pass
    transaction.rollback.assert_called_once()
    transaction.commit.assert_not_called()


def test_session_ownership_loss_cannot_commit():
    store, connection, transaction = fake_store([1, 0, 1])
    with pytest.raises(ValueError, match="ownership was lost"):
        with locking.mysql_unit_of_work(store):
            pass
    transaction.commit.assert_not_called()
    transaction.rollback.assert_called_once()


def test_failed_release_discards_physical_connection():
    store, connection, transaction = fake_store([1, 1, 0])
    with pytest.raises(ValueError, match="verify the saved result"):
        with locking.mysql_unit_of_work(store):
            pass
    transaction.commit.assert_called_once()
    connection.invalidate.assert_called_once()
    connection.close.assert_called_once()


def test_schema_failure_still_releases_session_lock():
    store, connection, transaction = fake_store([1, 1])
    store.ensure_schema.side_effect = ValueError("schema failure")
    with pytest.raises(ValueError, match="schema failure"):
        with locking.mysql_unit_of_work(store):
            pass
    assert "RELEASE_LOCK" in str(connection.execute.call_args.args[0])
    transaction.commit.assert_not_called()


def test_lock_identity_is_database_scoped_and_within_mysql_limit():
    assert locking.lock_name("APP") == locking.lock_name("app")
    assert locking.lock_name("app") != locking.lock_name("other")
    assert len(locking.lock_name("a" * 300)) <= 64


def test_stale_snapshot_merges_only_changed_fields():
    before = {"A":{"one":1}, "B":False}
    proposed = {"A":{"one":2}, "B":False}
    latest = {"A":{"one":1,"two":3}, "B":True,"C":4}
    assert _merge(before, proposed, latest) == {"A":{"one":2,"two":3},"B":True,"C":4}
    assert before == {"A":{"one":1}, "B":False}


def test_conflicting_stale_snapshot_rejected_without_write():
    with patch("backend.document_updates.read_json_document", return_value={"A":3}), patch("backend.document_updates.write_json_document") as write:
        with pytest.raises(ValueError, match="another session"):
            merge_session_document("unused", {"A":1}, {"A":2})
        write.assert_not_called()


def test_explicit_deletion_preserves_other_concurrent_additions():
    assert _merge({"A":1}, {}, {"A":1,"B":2}) == {"B":2}
    with pytest.raises(ValueError, match="another session"):
        _merge({"A":1}, {}, {"A":2})


def test_control_plane_remains_readable_when_database_is_unavailable(tmp_path):
    from backend.repositories.json_repository import JSONRepository
    path = tmp_path / "database_configurations.json"
    path.write_text("[]")
    with patch("backend.database.mysql_json_store.active_mysql_store", side_effect=ValueError("database unavailable")) as active:
        repository = JSONRepository(path)
        assert repository.get_all() == []
        repository.save_all([])
        active.assert_not_called()


def test_failed_database_acquisition_does_not_leak_local_lock():
    from backend.persistence_lock import PersistenceLock
    lock = PersistenceLock()
    with patch("backend.database.mysql_json_store.active_mysql_store", side_effect=ValueError("database unavailable")):
        with pytest.raises(ValueError, match="unavailable"):
            with lock:
                pass
    with lock.local_only():
        pass


def test_commit_error_rolls_back_and_does_not_expose_driver_details():
    store, connection, transaction = fake_store([1, 1, 1])
    transaction.commit.side_effect = OperationalError("SQL", {}, Exception("private driver detail"))
    with pytest.raises(ValueError, match="verify the saved result") as error:
        with locking.mysql_unit_of_work(store):
            pass
    assert "private driver detail" not in str(error.value)
    transaction.rollback.assert_called_once()


def test_explicit_target_can_be_used_without_reading_broken_active_profile():
    from backend.persistence_lock import PersistenceLock
    store, connection, transaction = fake_store([1, 1, 1])
    with patch("backend.database.mysql_json_store.active_mysql_store", side_effect=ValueError("old credentials invalid")) as active:
        with PersistenceLock().for_store(store):
            with locking.document_connection(store) as pinned:
                assert pinned is connection
        active.assert_not_called()
    transaction.commit.assert_called_once()


def test_different_session_for_same_database_cannot_deadlock_itself():
    first, connection, transaction = fake_store([1, 1])
    second, other_connection, other_transaction = fake_store([])
    with pytest.raises(ValueError, match="different connection"):
        with locking.mysql_unit_of_work(first):
            with locking.mysql_unit_of_work(second):
                pass
    second.engine.connect.assert_not_called()
    transaction.rollback.assert_called_once()
