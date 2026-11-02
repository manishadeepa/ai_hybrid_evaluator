import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
import reflex as rx

from backend.services.database_configuration_service import (
    DatabaseConfigurationService,
)
import backend.data_paths as data_paths
from backend.repositories.json_repository import JSONRepository
from backend.repositories.assessment_repository import AssessmentRepository
from backend.services.group_admin_service import GroupAdminService
from backend.services.master_admin_service import MasterAdminService
from ai_hybrid_evaluator.state.candidate_state import CandidateState
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState
from developer_console.developer_console.developer_console import State
import developer_console.developer_console.developer_console as console


class DatabaseConfigurationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = DatabaseConfigurationService(Path(self.temp.name))
        self.key_patch = patch.dict(
            "os.environ",
            {"AI_CONNECTION_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii")},
        )
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def test_folder_access_checks_server_directory_write_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.service.test_folder_access(folder)
            self.assertEqual(result, {"status": "success"})
            self.assertEqual(list(Path(folder).iterdir()), [])

        with self.assertRaisesRegex(ValueError, "absolute server folder path"):
            self.service.test_folder_access("relative-folder")
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.service.test_folder_access(str(Path(self.temp.name) / "missing"))

    def test_native_picker_is_attempted_only_on_windows(self):
        with patch(
            "backend.services.database_configuration_service.platform.system",
            return_value="Linux",
        ):
            self.assertIsNone(
                DatabaseConfigurationService.browse_native_folder(
                    self.temp.name
                )
            )

    def test_mysql_profile_is_encrypted_and_failed_retest_keeps_saved_config(self):
        form = {
            "host": "db.example.test",
            "port": "3306",
            "database": "evaluation",
            "username": "app-user",
            "password": "mysql-secret-value",
            "ssl_mode": "PREFERRED",
        }
        with patch.object(self.service, "_probe_mysql") as probe:
            saved = self.service.save_profile("mysql", form)
            probe.assert_called_once()
            self.service.test_mysql_connection(
                {
                    "host": "db.example.test",
                    "port": "3306",
                    "database": "evaluation",
                    "username": "",
                    "password": "",
                    "ssl_mode": "PREFERRED",
                }
            )
            self.assertEqual(
                probe.call_args_list[1].args[1],
                {"username": "app-user", "password": "mysql-secret-value"},
            )

            self.assertFalse(saved["active"])
            self.assertTrue(saved["credentials_configured"])
            self.assertNotIn("password", saved)
            contents_before_failure = self.service.config_path.read_text(
                encoding="utf-8"
            )
            self.assertNotIn("mysql-secret-value", contents_before_failure)
            self.assertNotIn("app-user", contents_before_failure)
            stored = json.loads(contents_before_failure)
            self.assertNotIn("password", stored[0])
            self.assertNotIn("username", stored[0]["configuration"])
            self.assertIn("credentials_encrypted", stored[0])

            probe.side_effect = ValueError("simulated connection failure")
            changed_form = {**form, "host": "unreachable.example.test"}
            with self.assertRaisesRegex(ValueError, "simulated connection failure"):
                self.service.save_profile("mysql", changed_form)

        self.assertEqual(
            self.service.config_path.read_text(encoding="utf-8"),
            contents_before_failure,
        )
        self.assertEqual(
            self.service.get_profile("mysql")["host"],
            "db.example.test",
        )

    def test_mysql_rejects_bad_port_without_attempting_connection(self):
        with patch.object(self.service, "_probe_mysql") as probe:
            with self.assertRaisesRegex(ValueError, "Port must be a number"):
                self.service.test_mysql_connection(
                    {
                        "host": "db.example.test",
                        "port": "70000",
                        "database": "evaluation",
                        "username": "app-user",
                        "password": "secret",
                    }
                )
        probe.assert_not_called()

    def test_api_uses_transport_probe_and_keeps_credentials_encrypted(self):
        form = {
            "service_name": "Vehicle Data Service",
            "base_url": "https://api.example.test",
            "api_version": "v1",
            "auth_type": "API Key",
            "api_key": "api-secret-value",
        }
        with patch.object(self.service, "_probe_api") as probe:
            self.assertEqual(
                self.service.test_api_connection(form),
                {"status": "success"},
            )
            probe.assert_called_once_with("https://api.example.test", "")
            profile = self.service.save_profile("api", form)

        self.assertFalse(profile["active"])
        self.assertTrue(profile["credentials_configured"])
        self.assertNotIn("api_key", profile)
        stored = self.service.config_path.read_text(encoding="utf-8")
        self.assertNotIn("api-secret-value", stored)
        self.assertNotIn("api_key", stored)

    def test_api_basic_auth_credentials_are_encrypted(self):
        form = {
            "service_name": "Basic Auth Service",
            "base_url": "https://api.example.test",
            "api_version": "v1",
            "auth_type": "Basic Auth",
            "api_username": "api-user",
            "api_password": "api-secret-value",
        }
        with patch.object(self.service, "_probe_api"):
            profile = self.service.save_profile("api", form)

        stored = self.service.config_path.read_text(encoding="utf-8")
        self.assertNotIn("api-user", stored)
        self.assertNotIn("api-secret-value", stored)
        self.assertNotIn("username", profile)
        self.assertNotIn("password", profile)
        self.assertEqual(
            self.service._credentials("api"),
            {"username": "api-user", "password": "api-secret-value"},
        )

    def test_api_test_failure_keeps_saved_profile_unchanged(self):
        form = {
            "service_name": "Vehicle Data Service",
            "base_url": "https://api.example.test",
            "api_version": "v1",
            "auth_type": "API Key",
            "api_key": "api-secret-value",
        }
        with patch.object(self.service, "_probe_api") as probe:
            saved = self.service.save_profile("api", form)
            before_failure = self.service.config_path.read_text(encoding="utf-8")
            probe.side_effect = ValueError("simulated endpoint failure")
            with self.assertRaisesRegex(ValueError, "simulated endpoint failure"):
                self.service.save_profile(
                    "api", {**form, "base_url": "https://unreachable.example.test"}
                )

        self.assertFalse(saved["active"])
        self.assertEqual(
            self.service.config_path.read_text(encoding="utf-8"), before_failure
        )
        self.assertEqual(
            self.service.get_profile("api")["base_url"],
            "https://api.example.test",
        )

    def test_api_requires_matching_credentials_and_secure_remote_transport(self):
        with self.assertRaisesRegex(ValueError, "API Key is required"):
            self.service.test_api_connection(
                {
                    "service_name": "Service",
                    "base_url": "https://api.example.test",
                    "api_version": "v1",
                    "auth_type": "API Key",
                }
            )

        with self.assertRaisesRegex(ValueError, "Use HTTPS"):
            self.service.test_api_connection(
                {
                    "service_name": "Service",
                    "base_url": "http://api.example.test",
                    "api_version": "v1",
                    "auth_type": "None",
                }
            )

    def test_ca_upload_rejects_non_certificate_content(self):
        with self.assertRaisesRegex(ValueError, "valid X.509 certificate"):
            self.service.store_ca_certificate("ca.pem", b"not a certificate")
        self.assertFalse(self.service.certificate_dir.exists())

    def test_database_management_pages_construct(self):
        self.assertIsNotNone(console.folder_configuration_page())
        self.assertIsNotNone(console.mysql_configuration_page())
        self.assertIsNotNone(console.api_configuration_page())

    def test_database_actions_require_developer_authentication(self):
        root_state = rx.State(_reflex_internal_init=True)
        state = asyncio.run(root_state.get_state(State))

        async def run_actions():
            await state.test_folder_access()
            await state.save_folder_configuration()
            await state.test_mysql_connection()
            await state.save_mysql_configuration()
            await state.test_api_connection()
            await state.save_api_configuration()

        asyncio.run(run_actions())
        self.assertEqual(
            state.database_error,
            "Sign in to the developer console to manage database settings.",
        )

    def test_native_folder_picker_selection_updates_only_form_path(self):
        root_state = rx.State(_reflex_internal_init=True)
        state = asyncio.run(root_state.get_state(State))
        state.is_authenticated = True
        state.folder_path = str(Path(self.temp.name))
        selected_path = str(Path(self.temp.name) / "selected")
        with (
            patch.object(
                console.DatabaseConfigurationService,
                "browse_native_folder",
                return_value=selected_path,
            ) as native_picker,
            patch.object(
                console.State, "_load_folder_browser_directory"
            ) as fallback,
        ):
            asyncio.run(state.open_folder_browser())

        self.assertEqual(state.folder_path, selected_path)
        self.assertFalse(state.folder_browser_open)
        self.assertEqual(state.database_test_status, "Not tested yet")
        native_picker.assert_called_once()
        fallback.assert_not_called()

    def test_native_picker_cancel_keeps_form_path_without_fallback(self):
        root_state = rx.State(_reflex_internal_init=True)
        state = asyncio.run(root_state.get_state(State))
        state.is_authenticated = True
        original_path = str(Path(self.temp.name))
        state.folder_path = original_path
        with (
            patch.object(
                console.DatabaseConfigurationService,
                "browse_native_folder",
                return_value="",
            ),
            patch.object(
                console.State, "_load_folder_browser_directory"
            ) as fallback,
        ):
            asyncio.run(state.open_folder_browser())

        self.assertEqual(state.folder_path, original_path)
        self.assertFalse(state.folder_browser_open)
        fallback.assert_not_called()

    def test_unavailable_native_picker_opens_existing_server_browser(self):
        root_state = rx.State(_reflex_internal_init=True)
        state = asyncio.run(root_state.get_state(State))
        state.is_authenticated = True
        state.folder_path = str(Path(self.temp.name))
        with (
            patch.object(
                console.DatabaseConfigurationService,
                "browse_native_folder",
                return_value=None,
            ),
            patch.object(
                console.DatabaseConfigurationService,
                "browse_directories",
                return_value={
                    "path": str(Path(self.temp.name).resolve()),
                    "parent": str(Path(self.temp.name).resolve().parent),
                    "entries": [],
                },
            ) as server_browser,
        ):
            asyncio.run(state.open_folder_browser())

        self.assertTrue(state.folder_browser_open)
        self.assertIn("native folder picker is unavailable", state.database_message)
        server_browser.assert_called_once()

    def test_successful_save_clears_credentials_from_console_form_state(self):
        root_state = rx.State(_reflex_internal_init=True)
        state = asyncio.run(root_state.get_state(State))
        state.is_authenticated = True
        state.mysql_host = "db.example.test"
        state.mysql_database = "evaluation"
        state.mysql_username = "app-user"
        state.mysql_password = "mysql-secret-value"
        state.api_service_name = "Service"
        state.api_base_url = "https://api.example.test"
        state.api_version = "v1"
        state.api_auth_type = "Basic Auth"
        state.api_username = "api-user"
        state.api_password = "api-secret-value"

        with (
            patch.object(console, "DatabaseConfigurationService", return_value=self.service),
            patch.object(self.service, "_probe_mysql"),
            patch.object(self.service, "_probe_api"),
        ):
            async def save_profiles():
                await state.save_mysql_configuration()
                await state.save_api_configuration()

            asyncio.run(save_profiles())

        self.assertEqual(state.mysql_username, "")
        self.assertEqual(state.mysql_password, "")
        self.assertEqual(state.api_username, "")
        self.assertEqual(state.api_password, "")
        stored = self.service.config_path.read_text(encoding="utf-8")
        self.assertNotIn("app-user", stored)
        self.assertNotIn("mysql-secret-value", stored)
        self.assertNotIn("api-user", stored)
        self.assertNotIn("api-secret-value", stored)

    def test_folder_activation_migrates_data_and_reroutes_existing_repositories(self):
        source = Path(self.temp.name) / "current"
        destination = Path(self.temp.name) / "selected"
        source.mkdir()
        destination.mkdir()
        source_file = source / "candidates.json"
        source_file.write_text('[{"candidate_id":"C-1"}]', encoding="utf-8")
        (source / "database_configurations.json").write_text(
            '[{"profile_type":"mysql"}]', encoding="utf-8"
        )
        certificate_dir = source / "db_ca_certs"
        certificate_dir.mkdir()
        (certificate_dir / "ca.pem").write_text("certificate", encoding="utf-8")
        (destination / "keep.json").write_text("[]", encoding="utf-8")
        with (
            patch.object(data_paths, "DEFAULT_DATA_DIR", source),
            patch.object(data_paths, "DATA_LOCATION_FILE", Path(self.temp.name) / "stable.json"),
        ):
            data_paths.save_active_data_dir(source)
            repository = JSONRepository(source_file)
            self.assertEqual(
                CandidateState._get_candidate_feedback_file_path(),
                source.resolve() / "candidate_feedbacks.json",
            )
            self.assertEqual(
                FacilitatorState._get_weightages_file_path(),
                source.resolve() / "assessment_weightages.json",
            )

            active = self.service.activate_data_folder(destination)

            self.assertEqual(active, destination.resolve())
            self.assertEqual(data_paths.get_active_data_dir(), destination.resolve())
            self.assertEqual(
                CandidateState._get_candidate_feedback_file_path(),
                destination.resolve() / "candidate_feedbacks.json",
            )
            self.assertEqual(
                FacilitatorState._get_weightages_file_path(),
                destination.resolve() / "assessment_weightages.json",
            )
            self.assertEqual(repository.get_all(), [{"candidate_id": "C-1"}])
            self.assertTrue(source_file.exists())
            self.assertTrue((source / "database_configurations.json").exists())
            self.assertFalse((destination / "database_configurations.json").exists())
            self.assertTrue((source / "db_ca_certs" / "ca.pem").exists())
            self.assertFalse((destination / "db_ca_certs").exists())
            self.assertTrue((destination / "keep.json").exists())
            self.assertEqual(
                (destination / "candidates.json").read_text(encoding="utf-8"),
                source_file.read_text(encoding="utf-8"),
            )
            (destination / "candidates.json").write_text("[]", encoding="utf-8")
            self.assertEqual(
                source_file.read_text(encoding="utf-8"), '[{"candidate_id":"C-1"}]'
            )

    def test_folder_migration_preserves_assessment_and_admin_login_data(self):
        source = Path(self.temp.name) / "current"
        destination = Path(self.temp.name) / "selected"
        source.mkdir()
        destination.mkdir()
        stable_path = Path(self.temp.name) / "stable.json"
        with (
            patch.object(data_paths, "DEFAULT_DATA_DIR", source),
            patch.object(data_paths, "DATA_LOCATION_FILE", stable_path),
        ):
            data_paths.save_active_data_dir(source)
            assessment_repository = AssessmentRepository(source / "assessments.json")
            assessment_repository.save_all(
                [{"assessment_id": "A-1", "name": "Assessment"}]
            )
            group_admins = GroupAdminService(source / "group_admins.json")
            group_admins.create("group-user", "group-password")
            master_admins = MasterAdminService(source / "master_admin.json")
            master_admins.create("master-user", "master-password")

            self.service.activate_data_folder(destination)

            self.assertEqual(
                assessment_repository.get_all(),
                [{"assessment_id": "A-1", "name": "Assessment"}],
            )
            self.assertIsNotNone(
                group_admins.authenticate("group-user", "group-password")
            )
            self.assertIsNotNone(
                master_admins.authenticate("master-user", "master-password")
            )
            self.assertTrue((source / "group_admins.json").exists())
            self.assertTrue((source / "master_admin.json").exists())

    def test_folder_conflict_does_not_overwrite_or_activate(self):
        source = Path(self.temp.name) / "current"
        destination = Path(self.temp.name) / "selected"
        source.mkdir()
        destination.mkdir()
        (source / "assessments.json").write_text('[{"id":"source"}]', encoding="utf-8")
        target_file = destination / "assessments.json"
        target_file.write_text('[{"id":"target"}]', encoding="utf-8")
        stable_path = Path(self.temp.name) / "stable.json"
        with (
            patch.object(data_paths, "DEFAULT_DATA_DIR", source),
            patch.object(data_paths, "DATA_LOCATION_FILE", stable_path),
        ):
            data_paths.save_active_data_dir(source)

            with self.assertRaisesRegex(ValueError, "files that differ"):
                self.service.activate_data_folder(destination)

            self.assertEqual(data_paths.get_active_data_dir(), source.resolve())
            self.assertEqual(
                target_file.read_text(encoding="utf-8"), '[{"id":"target"}]'
            )

    def test_folder_access_failure_does_not_activate(self):
        source = Path(self.temp.name) / "current"
        source.mkdir()
        stable_path = Path(self.temp.name) / "stable.json"
        with (
            patch.object(data_paths, "DEFAULT_DATA_DIR", source),
            patch.object(data_paths, "DATA_LOCATION_FILE", stable_path),
        ):
            data_paths.save_active_data_dir(source)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                self.service.activate_data_folder(Path(self.temp.name) / "missing")
            self.assertEqual(data_paths.get_active_data_dir(), source.resolve())

    def test_legacy_state_files_are_copied_to_default_without_removing_source(self):
        project = Path(self.temp.name) / "project"
        default = project / "backend" / "data"
        legacy = project / "ai_hybrid_evaluator" / "data"
        legacy.mkdir(parents=True)
        default.mkdir(parents=True)
        legacy_file = legacy / "assessment_weightages.json"
        legacy_file.write_text('{"assessment":{}}', encoding="utf-8")
        with (
            patch.object(data_paths, "PROJECT_ROOT", project),
            patch.object(data_paths, "DEFAULT_DATA_DIR", default),
            patch.object(data_paths, "DATA_LOCATION_FILE", project / "backend" / "data_location.json"),
        ):
            self.assertEqual(data_paths.get_active_data_dir(), default)
            self.assertEqual(
                (default / legacy_file.name).read_text(encoding="utf-8"),
                legacy_file.read_text(encoding="utf-8"),
            )
            self.assertTrue(legacy_file.exists())


if __name__ == "__main__":
    unittest.main()
