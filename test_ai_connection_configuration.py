import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet

from backend.repositories.ai_connection_repository import AIConnectionRepository
from backend.services.ai_connection_service import (
    AIConnectionService,
    AI_EVALUATION_NOT_CONFIGURED,
)


class AIConnectionConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "connections.json"
        self.repository = AIConnectionRepository(self.path)
        self.key = Fernet.generate_key()
        self.api_key = "admin-settings-secret"
        encrypted = Fernet(self.key).encrypt(self.api_key.encode()).decode("ascii")
        self.repository.save_and_activate(
            {
                "connection_id": "saved-connection",
                "name": "Admin Settings",
                "provider": "azure",
                "endpoint": "https://example.invalid",
                "model": "saved-deployment",
                "api_version": "2024-12-01-preview",
                "cert_path": "",
                "api_key_encrypted": encrypted,
                "key_configured": True,
                "status": "success",
                "active": True,
            }
        )
        self.environment = patch.dict(
            os.environ,
            {
                "APP_CREDENTIAL_ENCRYPTION_KEY": self.key.decode("ascii"),
                "OPENAI_API_KEY": "environment-must-not-be-used",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.service = AIConnectionService(self.repository)

    def test_client_uses_saved_admin_settings_and_keeps_secret_private(self):
        client = Mock()
        transport = Mock()
        with patch.object(
            self.service,
            "_make_client",
            return_value=(client, transport),
        ) as make_client:
            result = self.service.get_active_client()

        config = make_client.call_args.args[0]
        self.assertEqual(config["api_key"], self.api_key)
        self.assertEqual(config["model"], "saved-deployment")
        self.assertEqual(config["endpoint"], "https://example.invalid")
        self.assertEqual(result, (client, "saved-deployment", transport))

        public = self.service.get_active_public()
        self.assertNotIn("api_key", public)
        self.assertNotIn("api_key_encrypted", public)
        self.assertNotIn(self.api_key, repr(public))
        self.assertNotIn(self.api_key, repr(result))

    def test_environment_api_key_is_not_a_fallback(self):
        empty = AIConnectionService(AIConnectionRepository(
            Path(self.temp.name) / "empty.json"
        ))
        with patch.object(empty, "_make_client") as make_client:
            with self.assertRaisesRegex(
                ValueError,
                "AI evaluation is not configured. Please contact an administrator to check Admin Settings.",
            ):
                empty.get_active_client()
        make_client.assert_not_called()

    def test_saved_configuration_validation_initializes_no_network_request(self):
        transport = Mock()
        with patch.object(
            self.service,
            "_make_client",
            return_value=(Mock(), transport),
        ) as make_client:
            self.assertIsNone(self.service.validate_active_configuration())
        self.assertEqual(make_client.call_args.args[0]["api_key"], self.api_key)
        transport.close.assert_called_once_with()

    def test_invalid_saved_credentials_use_safe_actionable_error(self):
        record = self.repository.get_active()
        record["api_key_encrypted"] = "invalid-ciphertext"
        self.repository.save_and_activate(record)
        with self.assertRaisesRegex(ValueError, AI_EVALUATION_NOT_CONFIGURED) as raised:
            self.service.validate_active_configuration()
        self.assertNotIn(self.api_key, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
