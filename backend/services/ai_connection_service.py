import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

from backend.repositories.ai_connection_repository import (
    AIConnectionRepository,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AIConnectionService:
    def __init__(self, repository=None):
        self.repository = (
            repository
            or AIConnectionRepository()
        )

        load_dotenv(
            PROJECT_ROOT / ".env",
            override=False,
        )

    def _cipher(self):
        key = os.getenv(
            "AI_CONNECTION_ENCRYPTION_KEY"
        )

        if not key:
            raise ValueError(
                "AI_CONNECTION_ENCRYPTION_KEY is missing from .env."
            )

        try:
            return Fernet(key.encode("utf-8"))
        except Exception as exc:
            raise ValueError(
                "AI_CONNECTION_ENCRYPTION_KEY is invalid."
            ) from exc

    @staticmethod
    def _normalize(form):
        name = str(
            form.get("name", "")
        ).strip()

        endpoint = str(
            form.get("endpoint", "")
        ).strip().rstrip("/")

        model = str(
            form.get("model", "")
        ).strip()

        api_version = str(
            form.get("api_version", "")
        ).strip()

        cert_path = str(
            form.get("cert_path", "")
        ).strip()

        api_key = str(
            form.get("api_key", "")
        ).strip()

        if not name:
            raise ValueError(
                "Connection Name is required."
            )

        if not api_key:
            raise ValueError(
                "API Key is required."
            )

        # No provider selector exists in the UI.
        # Endpoint present = Azure.
        # Endpoint blank = direct OpenAI.
        provider = (
            "azure"
            if endpoint
            else "openai"
        )

        if provider == "azure":
            if not model:
                raise ValueError(
                    "Azure requires a deployment name."
                )

            if not api_version:
                raise ValueError(
                    "Azure requires an API version."
                )

            parsed = urlparse(endpoint)

            if (
                parsed.scheme != "https"
                or not parsed.netloc
            ):
                raise ValueError(
                    "Azure endpoint must be a valid HTTPS URL."
                )

        if cert_path and not Path(cert_path).is_file():
            raise ValueError(
                "CA certificate must be a readable file "
                "on the server."
            )

        return {
            "name": name,
            "provider": provider,
            "endpoint": endpoint,
            "model": model,
            "api_version": api_version,
            "cert_path": cert_path,
            "api_key": api_key,
        }

    @staticmethod
    def _make_client(config):
        http_client = httpx.Client(
            verify=config["cert_path"] or True,
            timeout=15.0,
        )

        if config["provider"] == "azure":
            client = AzureOpenAI(
                api_key=config["api_key"],
                azure_endpoint=config["endpoint"],
                api_version=config["api_version"],
                http_client=http_client,
                timeout=15.0,
                max_retries=0,
            )
        else:
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["endpoint"] or None,
                http_client=http_client,
                timeout=15.0,
                max_retries=0,
            )

        return client, http_client

    def test_connection(self, form):
        config = self._normalize(form)

        client, http_client = self._make_client(config)

        try:
            if config["provider"] == "azure":
                client.chat.completions.create(
                    model=config["model"],
                    messages=[
                        {
                            "role": "user",
                            "content": "Reply OK.",
                        }
                    ],
                    max_tokens=1,
                )
            else:
                client.models.list()

        except Exception as exc:
            raise ValueError(
                f"Connection test failed ({type(exc).__name__})."
            ) from exc

        finally:
            http_client.close()

        return {
            "status": "success",
            "last_tested_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
        }

    def save_and_activate(self, form):
        config = self._normalize(form)

        # Always test immediately before saving.
        self.test_connection(form)

        encrypted_key = (
            self._cipher()
            .encrypt(
                config["api_key"].encode("utf-8")
            )
            .decode("ascii")
        )

        record = {
            "connection_id": str(uuid.uuid4()),
            "name": config["name"],
            "provider": config["provider"],
            "endpoint": config["endpoint"],
            "model": config["model"],
            "api_version": config["api_version"],
            "cert_path": config["cert_path"],
            "api_key_encrypted": encrypted_key,
            "key_configured": True,
            "last_tested_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
            "status": "success",
            "active": True,
        }

        return self.repository.save_and_activate(
            record
        )

    def get_active_public(self):
        record = self.repository.get_active()

        if not record:
            return None

        return {
            key: record.get(key, "")
            for key in (
                "connection_id",
                "name",
                "provider",
                "endpoint",
                "model",
                "api_version",
                "cert_path",
                "last_tested_at",
                "status",
            )
        } | {
            "key_configured": bool(
                record.get("api_key_encrypted")
            )
        }

    def get_active_client(self):
        record = self.repository.get_active()

        if not record:
            return None

        encrypted_key = record.get(
            "api_key_encrypted"
        )

        if not encrypted_key:
            raise ValueError(
                "The active AI connection has no API key."
            )

        model = record.get(
            "model",
            "",
        ).strip()

        if not model:
            raise ValueError(
                "Set a model/deployment before "
                "running AI evaluation."
            )

        config = {
            "provider": record["provider"],
            "endpoint": record.get(
                "endpoint",
                "",
            ),
            "model": model,
            "api_version": record.get(
                "api_version",
                "",
            ),
            "cert_path": record.get(
                "cert_path",
                "",
            ),
            "api_key": (
                self._cipher()
                .decrypt(
                    encrypted_key.encode("ascii")
                )
                .decode("utf-8")
            ),
        }

        client, http_client = self._make_client(
            config
        )

        return client, model, http_client