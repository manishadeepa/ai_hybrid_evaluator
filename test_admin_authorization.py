"""Admin handler authorization regressions; services are always disposable fakes."""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest

from ai_hybrid_evaluator.state.admin_authorization import (
    has_admin_session,
    is_verified_admin_session,
)
from ai_hybrid_evaluator.state.auth_state import AuthState


ROOT = Path(__file__).parent
ADMIN_ROLES = {"Master Admin", "Group Admin"}


class FakeRx:
    class toast:
        @staticmethod
        def success(*args, **kwargs):
            return ("success", args)

        @staticmethod
        def error(*args, **kwargs):
            return ("error", args)

        @staticmethod
        def info(*args, **kwargs):
            return ("info", args)

    @staticmethod
    def redirect(path):
        return ("redirect", path)


def extract_state(path, class_name, names, namespace):
    source_path = ROOT / path
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    methods = {}
    for node in cls.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in names
        ):
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(source_path), "exec"), namespace)
            methods[node.name] = namespace[node.name]
    return type(f"{class_name}Harness", (), methods)


def make_state(harness, role):
    state = harness()
    auth = SimpleNamespace(
        is_authenticated=role in ADMIN_ROLES,
        admin_role=role or "",
        admin_email="admin@example.test" if role in ADMIN_ROLES else "",
    )

    async def get_state(_state_class):
        return auth

    state.get_state = get_state
    return state


class AdminAuthorizationTests(unittest.TestCase):
    def namespace(self, **values):
        return {
            "has_admin_session": has_admin_session,
            "is_verified_admin_session": is_verified_admin_session,
            "rx": FakeRx,
            **values,
        }

    def test_auth_state_accepts_only_verified_admin_roles(self):
        valid = SimpleNamespace(
            is_authenticated=True,
            admin_role="Master Admin",
            admin_email="master@example.test",
        )
        self.assertTrue(is_verified_admin_session(valid))
        valid.admin_role = "Group Admin"
        self.assertTrue(is_verified_admin_session(valid))
        valid.admin_role = "Candidate"
        self.assertFalse(is_verified_admin_session(valid))
        valid.is_authenticated = False
        valid.admin_role = "Master Admin"
        self.assertFalse(is_verified_admin_session(valid))

    def test_non_admin_roles_are_denied_before_loaders_and_savers(self):
        service_calls = []

        class NoCall:
            def __init__(self, *args, **kwargs):
                service_calls.append(type(self).__name__)

            def __getattr__(self, name):
                def called(*args, **kwargs):
                    service_calls.append(name)
                    raise AssertionError(f"Denied handler called {name}")
                return called

        roles = (None, "Candidate", "Facilitator")
        for role in roles:
            candidate_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {
                    "load_persisted_candidates",
                    "set_new_candidate_id",
                    "add_candidate",
                    "save_edit_candidate",
                    "confirm_delete_candidate",
                },
                self.namespace(
                    CandidateManagementService=NoCall,
                    Candidate=dict,
                    SHARED_CANDIDATES=[],
                    EMAIL_REGEX=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                    find_employee_by_id=NoCall,
                    re=__import__("re"),
                ),
            )
            candidate = make_state(candidate_harness, role)
            candidate.new_candidate_id = "C1"
            candidate.new_candidate_name = "Dummy"
            candidate.new_candidate_email = "dummy@example.test"
            candidate.new_candidate_password = "dummy-pass"
            candidate.new_candidate_department = ""
            candidate.candidate_password_hash_only_ids = []
            candidate.candidates = []
            candidate.set_show_add_candidate = lambda _value: None
            self.assertEqual(
                asyncio.run(candidate.set_new_candidate_id("DUMMY-C1")),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(candidate.load_persisted_candidates()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(candidate.add_candidate()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(candidate.save_edit_candidate()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(candidate.confirm_delete_candidate()),
                ("redirect", "/signin"),
            )

            facilitator_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {
                    "load_persisted_facilitators",
                    "add_facilitator",
                    "save_edit_facilitator",
                    "confirm_delete_facilitator",
                },
                self.namespace(
                    FacilitatorRepository=NoCall,
                    SHARED_FACILITATORS=[],
                    Facilitator=dict,
                    FACILITATOR_ID_REGEX=r"^F\d{3}$",
                    EMAIL_REGEX=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                    PHONE_REGEX=r"^\d{10}$",
                    re=__import__("re"),
                ),
            )
            facilitator = make_state(facilitator_harness, role)
            facilitator.facilitators = []
            facilitator.new_facilitator_empid = "F001"
            facilitator.new_facilitator_name = "Dummy"
            facilitator.new_facilitator_email = "dummy@example.test"
            facilitator.new_facilitator_phone = "1234567890"
            facilitator.new_facilitator_password = "dummy-pass"
            facilitator.set_show_add_facilitator = lambda _value: None
            self.assertEqual(
                asyncio.run(facilitator.load_persisted_facilitators()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(facilitator.add_facilitator()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(facilitator.save_edit_facilitator()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(facilitator.confirm_delete_facilitator()),
                ("redirect", "/signin"),
            )

            assessment_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {"load_persisted_assessments", "load_persisted_assessments_async",
                 "add_assessment", "save_edit_assessment",
                 "confirm_delete_assessment", "set_test_date",
                 "add_test_to_selected_assessment",
                 "remove_test_from_selected_assessment"},
                self.namespace(AssessmentService=NoCall),
            )
            assessment = make_state(assessment_harness, role)
            assessment._load_persisted_assessments = lambda: service_calls.append("assessment loader")
            self.assertEqual(
                asyncio.run(assessment.load_persisted_assessments_async()),
                ("redirect", "/signin"),
            )
            assessment._persist_assessment_record = lambda *_args, **_kwargs: service_calls.append("assessment save")
            assessment.new_assessment_name = "Dummy"
            assessment.new_assessment_facilitator_ids = ["F001"]
            assessment.facilitators = [{"emp_id": "F001", "name": "Dummy"}]
            assessment.new_assessment_date = ""
            assessment.new_assessment_candidate_ids = []
            assessment.new_assessment_status = "Scheduled"
            assessment.set_show_add_assessment = lambda _value: None
            self.assertEqual(
                asyncio.run(assessment.load_persisted_assessments()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(assessment.add_assessment()),
                ("redirect", "/signin"),
            )
            for name, args in (
                ("save_edit_assessment", ()),
                ("confirm_delete_assessment", ()),
                ("set_test_date", ("Dummy", "invalid")),
                ("add_test_to_selected_assessment", ()),
                ("remove_test_from_selected_assessment", ("Dummy",)),
            ):
                self.assertEqual(
                    asyncio.run(getattr(assessment, name)(*args)),
                    ("redirect", "/signin"),
                )

            settings_harness = extract_state(
                Path("ai_hybrid_evaluator/pages/admin/settings.py"),
                "SettingsState",
                {"_connection_form", "load_active_connection", "ai_save_and_use",
                 "_require_master_admin", "load_admin_accounts", "create_admin",
                 "save_admin_changes", "confirm_delete_admin"},
                self.namespace(
                    AuthState=AuthState,
                    AIConnectionService=NoCall,
                    MasterAdminService=NoCall,
                    GroupAdminService=NoCall,
                ),
            )
            settings = make_state(settings_harness, role)
            settings._connection_form = lambda: {"name": "dummy"}
            settings.new_admin_username = "dummy"
            settings.new_admin_password = "dummy-pass"
            settings.new_admin_confirm_password = "dummy-pass"
            settings.edit_admin_index = 0
            settings.admin_accounts = [{"is_master": False}]
            settings.delete_admin_username = "dummy"
            self.assertEqual(
                asyncio.run(settings.load_active_connection()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(settings.ai_save_and_use()),
                ("redirect", "/signin"),
            )
            self.assertIsNone(asyncio.run(settings.create_admin()))
            self.assertIsNone(asyncio.run(settings.save_admin_changes()))
            self.assertIsNone(asyncio.run(settings.confirm_delete_admin()))

            feedback_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminFeedbackState",
                {"on_load", "export_feedback"},
                self.namespace(asyncio=asyncio, AssessmentService=NoCall),
            )
            feedback = make_state(feedback_harness, role)
            feedback._read_feedback_data = lambda: service_calls.append("feedback loader")
            feedback.filtered_entries = []
            feedback.active_tab = "candidate"
            self.assertEqual(
                asyncio.run(feedback.on_load()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(feedback.export_feedback()),
                ("redirect", "/signin"),
            )

            report_harness = extract_state(
                Path("ai_hybrid_evaluator/pages/admin/reports.py"),
                "AdminReportsPageState",
                {"on_load", "select_assessment"},
                self.namespace(AdminState=object, FacilitatorState=object),
            )
            report = make_state(report_harness, role)
            self.assertEqual(
                asyncio.run(report.on_load()),
                ("redirect", "/signin"),
            )
            self.assertEqual(
                asyncio.run(report.select_assessment("Dummy")),
                ("redirect", "/signin"),
            )

        self.assertEqual(service_calls, [])

    def test_both_admin_roles_keep_candidate_facilitator_assessment_and_settings_actions(self):
        calls = []
        for role in ("Master Admin", "Group Admin"):
            class CandidateService:
                def list_candidates(self, **_kwargs):
                    calls.append("candidate load")
                    return []

                def create_candidate(self, record):
                    calls.append("candidate save")
                    return {"candidate_id": record["candidate_id"], **record}

            candidate_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {"load_persisted_candidates", "add_candidate"},
                self.namespace(
                    CandidateManagementService=CandidateService,
                    Candidate=dict,
                    SHARED_CANDIDATES=[],
                    EMAIL_REGEX=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                    re=__import__("re"),
                ),
            )
            candidate = make_state(candidate_harness, role)
            candidate.candidates = []
            candidate.candidate_password_hash_only_ids = []
            candidate.new_candidate_id = "C1"
            candidate.new_candidate_name = "Dummy"
            candidate.new_candidate_email = "dummy@example.test"
            candidate.new_candidate_password = "dummy-pass"
            candidate.new_candidate_department = ""
            candidate.set_show_add_candidate = lambda _value: None
            candidate._load_persisted_candidates = lambda: calls.append("candidate load")
            candidate._load_employee_directory_profiles = lambda: None
            asyncio.run(candidate.load_persisted_candidates())
            asyncio.run(candidate.add_candidate())

            class FacilitatorRepository:
                def get_all(self):
                    calls.append("facilitator load")
                    return []

                def save(self, _record):
                    calls.append("facilitator save")

            facilitator_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {"load_persisted_facilitators", "add_facilitator"},
                self.namespace(
                    FacilitatorRepository=FacilitatorRepository,
                    SHARED_FACILITATORS=[],
                    Facilitator=dict,
                    FACILITATOR_ID_REGEX=r"^F\d{3}$",
                    EMAIL_REGEX=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                    PHONE_REGEX=r"^\d{10}$",
                    re=__import__("re"),
                ),
            )
            facilitator = make_state(facilitator_harness, role)
            facilitator.facilitators = []
            facilitator.new_facilitator_empid = "F001"
            facilitator.new_facilitator_name = "Dummy"
            facilitator.new_facilitator_email = "dummy@example.test"
            facilitator.new_facilitator_phone = "1234567890"
            facilitator.new_facilitator_password = "dummy-pass"
            facilitator.set_show_add_facilitator = lambda _value: None
            facilitator._load_persisted_facilitators = lambda: calls.append("facilitator load")
            asyncio.run(facilitator.load_persisted_facilitators())
            asyncio.run(facilitator.add_facilitator())

            assessment_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminState",
                {"load_persisted_assessments_async", "add_assessment"},
                self.namespace(AssessmentService=object),
            )
            assessment = make_state(assessment_harness, role)
            async def load_facilitators():
                calls.append("facilitator catalog")

            async def load_candidates():
                calls.append("candidate catalog")

            async def load_assessment_records(_legacy=None):
                calls.append("assessment load")
                return []

            assessment.load_persisted_facilitators = load_facilitators
            assessment.load_persisted_candidates = load_candidates
            assessment._load_assessment_records = load_assessment_records
            assessment._persist_assessment_record = lambda *_args, **_kwargs: calls.append("assessment save")
            assessment.new_assessment_name = "Dummy"
            assessment.new_assessment_facilitator_ids = ["F001"]
            assessment.facilitators = [{"emp_id": "F001", "name": "Dummy"}]
            assessment.new_assessment_date = ""
            assessment.new_assessment_candidate_ids = []
            assessment.new_assessment_status = "Scheduled"
            assessment.set_show_add_assessment = lambda _value: None
            asyncio.run(assessment.load_persisted_assessments_async())
            asyncio.run(assessment.add_assessment())

            class AIConnectionService:
                def save_and_activate(self, _form, **_kwargs):
                    calls.append("settings save")
                    return {
                        "connection_id": "dummy-id",
                        "name": "Dummy",
                        "endpoint": "",
                        "model": "",
                        "api_version": "",
                        "cert_path": "",
                        "last_tested_at": "",
                    }

            settings_harness = extract_state(
                Path("ai_hybrid_evaluator/pages/admin/settings.py"),
                "SettingsState",
                {"_connection_form", "ai_save_and_use"},
                self.namespace(AIConnectionService=AIConnectionService),
            )
            settings = make_state(settings_harness, role)
            settings._connection_form = lambda: {"name": "Dummy"}
            settings.ai_conn_editing_existing = False
            settings.ai_conn_edit_id = ""
            settings.ai_saved_name = ""
            asyncio.run(settings.ai_save_and_use())

            feedback_harness = extract_state(
                Path("ai_hybrid_evaluator/state/admin_state.py"),
                "AdminFeedbackState",
                {"export_feedback"},
                self.namespace(),
            )
            feedback = make_state(feedback_harness, role)
            feedback.filtered_entries = [{"id": "dummy"}]
            feedback.active_tab = "candidate"
            self.assertEqual(
                asyncio.run(feedback.export_feedback()),
                ("success", ("1 Candidate feedback records exported successfully!",)),
            )

            admin_state_class = type("AdminStateHarness", (), {})
            facilitator_state_class = type("FacilitatorStateHarness", (), {})
            report_harness = extract_state(
                Path("ai_hybrid_evaluator/pages/admin/reports.py"),
                "AdminReportsPageState",
                {"assessment_options", "on_load"},
                self.namespace(
                    AdminState=admin_state_class,
                    FacilitatorState=facilitator_state_class,
                ),
            )
            report = make_state(report_harness, role)
            report_auth = SimpleNamespace(
                is_authenticated=role in ADMIN_ROLES,
                admin_role=role,
                admin_email="admin@example.test" if role in ADMIN_ROLES else "",
            )

            async def report_get_state(state_class):
                if state_class is AuthState:
                    return report_auth
                if state_class is admin_state_class:
                    return SimpleNamespace(assessments=[])
                if state_class is facilitator_state_class:
                    return SimpleNamespace(selected_assessment_name="")
                raise AssertionError(f"Unexpected state requested: {state_class}")

            report.get_state = report_get_state
            self.assertEqual(asyncio.run(report.assessment_options()), [])
            self.assertIsNone(asyncio.run(report.on_load()))

        self.assertCountEqual(
            calls,
            [
                "candidate load", "candidate save",
                "facilitator load", "facilitator load", "facilitator save",
                "facilitator catalog", "candidate catalog",
                "assessment load", "assessment save",
                "settings save",
            ] * 2,
        )

    def test_group_admin_cannot_create_edit_or_delete_group_admin_accounts(self):
        calls = []

        class AccountService:
            def __init__(self, *args, **kwargs):
                calls.append("construct")

            def __getattr__(self, name):
                def called(*args, **kwargs):
                    calls.append(name)
                return called

        harness = extract_state(
            Path("ai_hybrid_evaluator/pages/admin/settings.py"),
            "SettingsState",
            {"_require_master_admin", "load_admin_accounts", "create_admin",
             "save_admin_changes", "confirm_delete_admin"},
            self.namespace(
                AuthState=AuthState,
                MasterAdminService=AccountService,
                GroupAdminService=AccountService,
            ),
        )
        state = make_state(harness, "Group Admin")
        state.new_admin_username = "another-admin"
        state.new_admin_password = "dummy-pass"
        state.new_admin_confirm_password = "dummy-pass"
        state.edit_admin_index = 0
        state.admin_accounts = [{"is_master": False}]
        state.edit_admin_username = "another-admin"
        state.delete_admin_username = "another-admin"

        self.assertIsNone(asyncio.run(state.load_admin_accounts()))
        asyncio.run(state.create_admin())
        asyncio.run(state.save_admin_changes())
        asyncio.run(state.confirm_delete_admin())

        self.assertEqual(calls, [])
        self.assertIn("Master Admin", state.add_admin_error)
        self.assertIn("Master Admin", state.edit_admin_error)
        self.assertIn("Master Admin", state.admin_management_error)

    def test_master_admin_can_manage_group_admin_accounts(self):
        operations = []
        group_accounts = [{"username": "old-admin", "password": "old-pass"}]

        class MasterAdminService:
            def get(self):
                return {"username": "master"}

        class GroupAdminService:
            def get_all(self):
                return list(group_accounts)

            def create(self, username, password):
                operations.append(("create", username))
                group_accounts.append({"username": username, "password": password})

            def update(self, old_username, username, password=None):
                operations.append(("update", old_username, username))
                account = next(
                    account for account in group_accounts
                    if account["username"] == old_username
                )
                account["username"] = username
                if password:
                    account["password"] = password

            def delete(self, username):
                operations.append(("delete", username))
                group_accounts[:] = [
                    account for account in group_accounts
                    if account["username"] != username
                ]

        harness = extract_state(
            Path("ai_hybrid_evaluator/pages/admin/settings.py"),
            "SettingsState",
            {"_require_master_admin", "load_admin_accounts", "create_admin",
             "save_admin_changes", "confirm_delete_admin"},
            self.namespace(
                AuthState=AuthState,
                MasterAdminService=MasterAdminService,
                GroupAdminService=GroupAdminService,
            ),
        )
        state = make_state(harness, "Master Admin")
        asyncio.run(state.load_admin_accounts())
        state.new_admin_username = "new-admin"
        state.new_admin_password = "new-pass"
        state.new_admin_confirm_password = "new-pass"
        asyncio.run(state.create_admin())

        state.edit_admin_index = 1
        state.edit_admin_original_username = "old-admin"
        state.edit_admin_username = "renamed-admin"
        state.edit_admin_password = ""
        state.edit_admin_confirm_password = ""
        asyncio.run(state.save_admin_changes())

        state.delete_admin_username = "renamed-admin"
        asyncio.run(state.confirm_delete_admin())

        self.assertEqual(
            operations,
            [
                ("create", "new-admin"),
                ("update", "old-admin", "renamed-admin"),
                ("delete", "renamed-admin"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
