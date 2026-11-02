import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import reflex as rx

from ai_hybrid_evaluator.services.mock_api import change_admin_password, mock_login
from ai_hybrid_evaluator.pages.admin.settings import SettingsState, access_control_card
from ai_hybrid_evaluator.state.auth_state import AuthState
from backend.services.group_admin_service import GroupAdminService
from backend.services.master_admin_service import MasterAdminService
from developer_console.developer_console.developer_console import State
import ai_hybrid_evaluator.pages.admin.settings as settings
import developer_console.developer_console.developer_console as console


class DeveloperConsoleAdminManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = GroupAdminService(Path(self.temp.name) / "group_admins.json")
        self.master_service = MasterAdminService(
            Path(self.temp.name) / "master_admin.json"
        )
        self.root_state = rx.State(_reflex_internal_init=True)
        self.state = asyncio.run(self.root_state.get_state(State))
        self.state.is_authenticated = True
        self.patches = [
            patch.object(console, "GroupAdminService", return_value=self.service),
            patch.object(
                console,
                "MasterAdminService",
                return_value=self.master_service,
            ),
        ]
        for active_patch in self.patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

    def test_console_loads_only_master_identity_and_preserves_group_credentials(self):
        self.service.create("Existing Group User", "existing-pass")
        self.master_service.create("Master User", "master-pass")

        self.state.load_admin_accounts()

        self.assertEqual(
            self.state.master_admin,
            {"username": "Master User"},
        )
        self.assertFalse(hasattr(self.state, "group_admins"))
        self.assertFalse(hasattr(self.state, "add_group_admin"))
        self.assertIsNotNone(
            self.service.authenticate("Existing Group User", "existing-pass")
        )

        page_text = str(console.admin_management_page())
        self.assertNotIn("Group Administrators", page_text)
        self.assertNotIn("Add Group Admin", page_text)
        self.assertNotIn("Group Admin", page_text)

    def test_main_app_master_admin_manages_group_admins_and_keeps_hashing(self):
        self.service.create("Existing Group User", "existing-pass")
        self.master_service.create("Master User", "master-pass")
        app_root_state = rx.State(_reflex_internal_init=True)
        app_state = asyncio.run(app_root_state.get_state(SettingsState))
        auth_state = asyncio.run(app_root_state.get_state(AuthState))
        auth_state.is_authenticated = True
        auth_state.admin_role = "Master Admin"

        with (
            patch.object(settings, "GroupAdminService", return_value=self.service),
            patch.object(
                settings, "MasterAdminService", return_value=self.master_service
            ),
        ):
            app_state.load_admin_accounts()

            self.assertTrue(
                all(
                    "salt" not in account and "password_hash" not in account
                    for account in app_state.admin_accounts
                )
            )
            asyncio.run(app_state.open_edit_admin_dialog(0))
            self.assertFalse(app_state.show_edit_admin_dialog)
            app_state.delete_admin_index = 0
            asyncio.run(app_state.confirm_delete_admin())
            self.assertIsNotNone(
                self.master_service.authenticate("Master User", "master-pass")
            )

            app_state.new_admin_username = "New Group Admin"
            app_state.new_admin_password = "initial-pass"
            app_state.new_admin_confirm_password = "initial-pass"
            asyncio.run(app_state.create_admin())
            self.assertIsNotNone(
                self.service.authenticate("New Group Admin", "initial-pass")
            )

            app_state.load_admin_accounts()
            self.assertEqual(
                [account["username"] for account in app_state.admin_accounts],
                ["Master User", "Existing Group User", "New Group Admin"],
            )
            self.assertEqual(
                [account["role"] for account in app_state.admin_accounts],
                ["Master Admin", "Group Admin", "Group Admin"],
            )
            asyncio.run(app_state.open_edit_admin_dialog(2))
            app_state.edit_admin_username = "Updated Group Admin"
            app_state.edit_admin_password = "reset-pass"
            app_state.edit_admin_confirm_password = "reset-pass"
            asyncio.run(app_state.save_admin_changes())
            self.assertIsNone(
                self.service.authenticate("New Group Admin", "initial-pass")
            )
            self.assertIsNotNone(
                self.service.authenticate("Updated Group Admin", "reset-pass")
            )

            with (
                patch(
                    "ai_hybrid_evaluator.services.mock_api.GroupAdminService",
                    return_value=self.service,
                ),
                patch(
                    "ai_hybrid_evaluator.services.mock_api.MasterAdminService",
                    return_value=self.master_service,
                ),
            ):
                self.assertTrue(
                    mock_login("Updated Group Admin", "reset-pass")["success"]
                )

            app_state.load_admin_accounts()
            asyncio.run(app_state.open_delete_admin_dialog(2))
            asyncio.run(app_state.confirm_delete_admin())
            app_state.load_admin_accounts()
            self.assertEqual(
                [account["username"] for account in app_state.admin_accounts],
                ["Master User", "Existing Group User"],
            )
            self.assertIsNone(
                self.service.authenticate("Updated Group Admin", "reset-pass")
            )
            self.assertIsNotNone(
                self.service.authenticate("Existing Group User", "existing-pass")
            )
            self.assertIsNotNone(
                self.master_service.authenticate("Master User", "master-pass")
            )

    def test_group_admin_cannot_manage_group_admin_accounts(self):
        self.service.create("Existing Group User", "existing-pass")
        self.master_service.create("Master User", "master-pass")
        app_root_state = rx.State(_reflex_internal_init=True)
        app_state = asyncio.run(app_root_state.get_state(SettingsState))
        auth_state = asyncio.run(app_root_state.get_state(AuthState))
        auth_state.is_authenticated = True
        auth_state.admin_role = "Administrator"
        app_state.load_admin_accounts()

        app_state.new_admin_username = "Unauthorized"
        app_state.new_admin_password = "unauthorized-pass"
        app_state.new_admin_confirm_password = "unauthorized-pass"

        with (
            patch.object(settings, "GroupAdminService", return_value=self.service),
            patch.object(
                settings, "MasterAdminService", return_value=self.master_service
            ),
        ):
            asyncio.run(app_state.create_admin())
            asyncio.run(app_state.open_edit_admin_dialog(1))
            self.assertFalse(app_state.show_edit_admin_dialog)
            app_state.edit_admin_index = 1
            app_state.edit_admin_username = "Unauthorized Rename"
            asyncio.run(app_state.save_admin_changes())
            asyncio.run(app_state.open_delete_admin_dialog(1))
            self.assertFalse(app_state.show_delete_admin_dialog)
            app_state.delete_admin_index = 1
            asyncio.run(app_state.confirm_delete_admin())

        self.assertIsNone(self.service.authenticate("Unauthorized", "unauthorized-pass"))
        self.assertIsNone(
            self.service.authenticate("Unauthorized Rename", "existing-pass")
        )
        self.assertIsNotNone(
            self.service.authenticate("Existing Group User", "existing-pass")
        )

    def test_access_control_shows_protected_master_and_group_admin_actions(self):
        page_text = str(access_control_card())
        self.assertIn("Add Admin", page_text)
        self.assertIn("Cannot be edited or removed.", page_text)
        self.assertIn("Edit", page_text)
        self.assertIn("Delete", page_text)
        self.assertNotIn("View Admin Credentials", page_text)

    def test_main_login_records_authenticated_admin_role(self):
        auth_root_state = rx.State(_reflex_internal_init=True)
        auth_state = asyncio.run(auth_root_state.get_state(AuthState))
        auth_state.signin_email = "Master User"
        auth_state.signin_password = "master-pass"

        with patch(
            "ai_hybrid_evaluator.state.auth_state.mock_login",
            return_value={
                "success": True,
                "employee_name": "Master User",
                "employee_id": "",
                "employee_mail": "Master User",
                "role": "Master Admin",
            },
        ):
            auth_state.sign_in()

        self.assertTrue(auth_state.is_authenticated)
        self.assertEqual(auth_state.admin_role, "Master Admin")
        auth_state.logout()
        self.assertEqual(auth_state.admin_role, "")

    def test_main_login_and_password_change_use_both_hashed_account_stores(self):
        self.master_service.create("Master User", "master-password")
        self.service.create("Group User", "group-password")

        with (
            patch(
                "ai_hybrid_evaluator.services.mock_api.MasterAdminService",
                return_value=self.master_service,
            ),
            patch(
                "ai_hybrid_evaluator.services.mock_api.GroupAdminService",
                return_value=self.service,
            ),
        ):
            master_login = mock_login("Master User", "master-password")
            group_login = mock_login("Group User", "group-password")
            master_change = change_admin_password(
                "Master User", "master-password", "new-master-password",
                "new-master-password",
            )
            group_change = change_admin_password(
                "Group User", "group-password", "new-group-password",
                "new-group-password",
            )
            self.assertTrue(mock_login("Master User", "new-master-password")["success"])
            self.assertTrue(mock_login("Group User", "new-group-password")["success"])

        self.assertEqual(master_login["role"], "Master Admin")
        self.assertEqual(group_login["role"], "Group Admin")
        self.assertTrue(master_change["success"])
        self.assertTrue(group_change["success"])
        self.assertIsNone(self.master_service.authenticate("Master User", "master-password"))
        self.assertIsNone(self.service.authenticate("Group User", "group-password"))

    def test_developer_can_create_edit_and_reset_master_admin(self):
        self.service.create("Existing Group User", "existing-pass")
        self.state.new_master_admin_username = "Master User"
        self.state.new_master_admin_password = "initial-master-pass"
        self.state.new_master_admin_confirm_password = "initial-master-pass"
        self.state.create_master_admin()
        self.assertIsNotNone(
            self.master_service.authenticate("Master User", "initial-master-pass")
        )
        with patch(
            "ai_hybrid_evaluator.services.mock_api.MasterAdminService",
            return_value=self.master_service,
        ):
            login_result = mock_login("Master User", "initial-master-pass")
        self.assertTrue(login_result["success"])
        self.assertEqual(login_result["role"], "Master Admin")

        self.state.open_edit_master_admin_dialog()
        self.state.edit_master_admin_username = "Primary Admin"
        self.state.save_master_admin_username()
        self.assertIsNotNone(
            self.master_service.authenticate("Primary Admin", "initial-master-pass")
        )

        self.state.reset_master_admin_password = "new-master-pass"
        self.state.reset_master_admin_confirm_password = "new-master-pass"
        self.state.reset_master_admin_password_now()
        self.assertIsNone(
            self.master_service.authenticate("Primary Admin", "initial-master-pass")
        )
        self.assertIsNotNone(
            self.master_service.authenticate("Primary Admin", "new-master-pass")
        )
        self.assertIsNotNone(
            self.service.authenticate("Existing Group User", "existing-pass")
        )

    def test_master_creation_is_blocked_without_developer_login(self):
        self.state.logout()
        self.state.new_master_admin_username = "Unauthorized Master"
        self.state.new_master_admin_password = "unauthorized-pass"
        self.state.new_master_admin_confirm_password = "unauthorized-pass"
        self.state.create_master_admin()
        self.assertIsNone(self.master_service.get())

    def test_console_login_uses_configured_environment_credentials(self):
        self.state.is_authenticated = False
        with patch.dict(
            os.environ,
            {
                "DEV_CONSOLE_USERNAME": "developer",
                "DEV_CONSOLE_PASSWORD": "private-password",
            },
        ):
            self.state.login(
                {"username": "developer", "password": "private-password"}
            )
        self.assertTrue(self.state.is_authenticated)

        self.state.logout()
        with patch.dict(
            os.environ,
            {"DEV_CONSOLE_USERNAME": "", "DEV_CONSOLE_PASSWORD": ""},
        ):
            self.state.login({"username": "developer", "password": "private-password"})
        self.assertFalse(self.state.is_authenticated)
        self.assertIn("not configured", self.state.login_error)
