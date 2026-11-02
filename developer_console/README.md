# Backend Developer Console

The console is a separate Reflex app. It manages the Master Admin account and database
configuration profiles; Group Admin accounts remain managed by the main app.

## Configure and run

1. Copy `.env.example` to `.env` and set private `DEV_CONSOLE_USERNAME` and
   `DEV_CONSOLE_PASSWORD` values. `.env` is ignored by Git.
2. From the repository root, start the console with:

   ```powershell
   Set-Location .\developer_console
   & ..\.venv\Scripts\python.exe -m reflex run --env prod
   ```

The console serves its UI on port 3001 and its Reflex backend on port 8001. Its source
adds the repository root to `sys.path`, so it can import the shared `backend` services
without copying those modules.

For encrypted MySQL/API credentials, configure `AI_CONNECTION_ENCRYPTION_KEY` in the
repository-root `.env` as a Fernet key. Generate a new key locally with:

```powershell
& ..\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep that key private and backed up; losing it makes saved credentials unreadable.
Saved MySQL/API profiles are pending only. JSON remains active unless the Folder Path
workflow successfully migrates the existing files and explicitly activates the
selected folder. The API checker verifies HTTPS transport only: no API contract or
authentication endpoint is configured, so it does not claim API authentication.
