import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
import reflex as rx
from cryptography.fernet import Fernet
from sqlalchemy.exc import SQLAlchemyError
from backend import data_paths as paths
from backend.repositories.json_repository import JSONRepository
from backend.services.database_configuration_service import DatabaseConfigurationService
import backend.services.database_configuration_service as db
import developer_console.developer_console.developer_console as console

@pytest.fixture
def folders(tmp_path, monkeypatch):
    source = tmp_path / "source"; source.mkdir()
    target = tmp_path / "target"; target.mkdir()
    stable = tmp_path / "console"; stable.mkdir()
    monkeypatch.setattr(paths, "DEFAULT_DATA_DIR", source)
    monkeypatch.setattr(paths, "DATA_LOCATION_FILE", tmp_path / "location.json")
    paths.save_active_data_dir(source)
    (source / "candidates.json").write_text('[{"candidate_id":"C1"}]')
    service = DatabaseConfigurationService(stable)
    return source, target, service

def manifests(service):
    return list((service.data_dir / ".storage_migrations").glob("*/manifest.json"))

def test_verified_backup_and_live_repository_rerouting(folders):
    source, target, service = folders
    repo = JSONRepository(source / "candidates.json")
    raw = (source / "candidates.json").read_bytes()
    assert service.activate_data_folder(target) == target.resolve()
    record = json.loads(manifests(service)[0].read_text())
    assert record["status"] == "activated"
    assert (manifests(service)[0].parent / "backup/candidates.json").read_bytes() == raw
    assert repo.get_all() == [{"candidate_id":"C1"}]
    repo.save_all([{"candidate_id":"C2"}])
    assert (source / "candidates.json").read_bytes() == raw
    assert json.loads((target / "candidates.json").read_text())[0]["candidate_id"] == "C2"

@pytest.mark.parametrize("failure", ["copy", "verification", "activation"])
def test_migration_failure_rolls_back_only_new_files(folders, monkeypatch, failure):
    source, target, service = folders
    keep = target / "existing.json"; keep.write_text("[]")
    config_before = paths.DATA_LOCATION_FILE.read_bytes()
    source_before = (source / "candidates.json").read_bytes()
    if failure == "copy":
        monkeypatch.setattr(db.shutil, "copy2", lambda *args: (_ for _ in ()).throw(OSError("copy failed")))
    elif failure == "verification":
        publish = service._publish_staged_file
        def corrupt(staged, destination, created):
            publish(staged, destination, created)
            destination.write_text("[]")
        monkeypatch.setattr(service, "_publish_staged_file", corrupt)
    else:
        monkeypatch.setattr(db, "save_active_data_dir", lambda *args: (_ for _ in ()).throw(OSError("activation failed")))
    with pytest.raises(ValueError, match="current storage is unchanged"):
        service.activate_data_folder(target)
    assert paths.DATA_LOCATION_FILE.read_bytes() == config_before
    assert (source / "candidates.json").read_bytes() == source_before
    assert keep.read_text() == "[]"
    assert not (target / "candidates.json").exists()
    assert json.loads(manifests(service)[0].read_text())["status"] == "failed_current_storage_unchanged"
    if failure != "copy":
        assert (manifests(service)[0].parent / "backup/candidates.json").read_bytes() == source_before

def test_conflict_is_detected_before_copying(folders):
    source, target, service = folders
    (target / "candidates.json").write_text("[]")
    with pytest.raises(ValueError, match="files that differ"):
        service.activate_data_folder(target)
    assert paths.get_active_data_dir() == source.resolve()
    assert (target / "candidates.json").read_text() == "[]"
    assert manifests(service) == []

def test_invalid_json_is_not_activated(folders):
    source, target, service = folders
    (source / "candidates.json").write_text("invalid")
    with pytest.raises(ValueError, match="Invalid JSON"):
        service.activate_data_folder(target)
    assert paths.get_active_data_dir() == source.resolve()

def test_selection_and_access_test_do_not_activate(folders):
    source, target, service = folders
    service.test_folder_access(target)
    assert paths.get_active_data_dir() == source.resolve()
    assert list(target.iterdir()) == []

def test_repository_writer_waits_for_verified_switch(folders, monkeypatch):
    source, target, service = folders
    repo = JSONRepository(source / "candidates.json")
    entered = threading.Event(); release = threading.Event(); written = threading.Event()
    publish = service._publish_staged_file
    def pause(*args):
        entered.set()
        assert release.wait(5)
        return publish(*args)
    monkeypatch.setattr(service, "_publish_staged_file", pause)
    def write():
        repo.save_all([{"candidate_id":"AFTER"}]); written.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        moving = pool.submit(service.activate_data_folder, target)
        try:
            assert entered.wait(5)
            writing = pool.submit(write)
            assert not written.wait(0.1)
        finally:
            release.set()
        moving.result(timeout=5); writing.result(timeout=5)
    assert json.loads((target / "candidates.json").read_text())[0]["candidate_id"] == "AFTER"
    assert json.loads((source / "candidates.json").read_text())[0]["candidate_id"] == "C1"

def test_api_is_https_only_even_for_localhost(tmp_path):
    service = DatabaseConfigurationService(tmp_path)
    with patch.object(service, "_probe_api") as probe:
        for url in ["http://localhost", "http://127.0.0.1", "https://host:0", "https://ho\nst/path"]:
            with pytest.raises(ValueError):
                service.test_api_connection({"service_name":"S", "base_url":url, "api_version":"v1", "auth_type":"None"})
        probe.assert_not_called()

def test_mysql_profile_activates_and_api_profile_remains_pending(folders, monkeypatch):
    source, target, service = folders
    monkeypatch.setenv("APP_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    config_before = paths.DATA_LOCATION_FILE.read_bytes()
    with (
        patch.object(service, "_probe_mysql"),
        patch.object(service, "_probe_api"),
        patch.object(service, "_migration_documents", return_value=[]),
        patch.object(db, "MySQLJSONStore"),
    ):
        mysql = service.save_profile("mysql", {"host":"db.test", "database":"D", "port":3306, "username":"private-user", "password":"private-pass"})
        api = service.save_profile("api", {"service_name":"S", "base_url":"https://api.test", "api_version":"v1", "auth_type":"Bearer Token", "token":"private-token"})
    assert mysql["active"] is True and mysql["status"] == "success"
    assert api["active"] is False and api["status"] == "pending"
    assert "required" in api["activation_requirements"]
    for result in (mysql, api):
        assert "credentials_encrypted" not in result
    raw = service.config_path.read_text()
    assert all(secret not in raw for secret in ["private-user", "private-pass", "private-token"])
    assert paths.DATA_LOCATION_FILE.read_bytes() == config_before
    assert service.get_profile("api")["validation_scope"] == "https_transport_only"

def test_mysql_error_does_not_expose_driver_secret():
    with patch.object(db, "create_engine", side_effect=SQLAlchemyError("private-password")):
        with pytest.raises(ValueError) as error:
            DatabaseConfigurationService._probe_mysql({"host":"db", "port":3306, "database":"D", "ssl_mode":"REQUIRED"}, {"username":"user", "password":"private-password"})
    assert "private-password" not in str(error.value)
    assert error.value.__suppress_context__

@pytest.mark.parametrize("port", [True, 1.5, 0, 65536, "bad"])
def test_invalid_mysql_port_rejected(port, tmp_path):
    service = DatabaseConfigurationService(tmp_path)
    with patch.object(service, "_probe_mysql") as probe:
        with pytest.raises(ValueError):service.test_mysql_connection({"host":"db", "database":"D", "port":port})
        probe.assert_not_called()

def test_forged_public_auth_flag_cannot_call_storage_actions():
    root = rx.State(_reflex_internal_init=True)
    state = asyncio.run(root.get_state(console.State))
    state.is_authenticated = True
    with patch.object(console, "DatabaseConfigurationService") as service:
        async def attempt():
            for method in [state.test_folder_access, state.save_folder_configuration, state.test_mysql_connection, state.save_mysql_configuration, state.test_api_connection, state.save_api_configuration]:
                await method()
        asyncio.run(attempt())
        service.assert_not_called()
    assert "Sign in" in state.database_error

def test_logout_clears_transient_database_secrets():
    root = rx.State(_reflex_internal_init=True)
    state = asyncio.run(root.get_state(console.State))
    state.mysql_password="mysql-secret";state.api_key="api-secret";state.api_token="token-secret"
    state.api_password="basic-secret";state.mysql_username="private-user";state.show_mysql_password=True
    state.logout()
    assert not any([state.mysql_password,state.api_key,state.api_token,state.api_password,state.mysql_username])
    assert not state.show_mysql_password
