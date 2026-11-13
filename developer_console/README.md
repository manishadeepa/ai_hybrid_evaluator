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

The app creates `backend/.credential_encryption.key` on first use to encrypt MySQL/API
credentials and Admin AI connections. Keep it private and preserve it across
deployments and backups; losing or changing it makes saved credentials unreadable.
Managed deployments may instead provide `APP_CREDENTIAL_ENCRYPTION_KEY` through the
host's secret manager. Database connection settings are entered in this console and
are not read from an application `.env` file.

Saving a tested MySQL profile activates it for application data. Existing JSON
repository data is imported without overwriting conflicting MySQL data. The API
checker verifies HTTPS transport only: no API contract or authentication endpoint is
configured, so it does not claim API authentication.

The compatibility layer stores each existing JSON data file as one JSON value in
MySQL to preserve current repository behavior. This is not a normalized schema, and
whole-collection writes are not a production-scale multi-instance design. Uploaded
assessment and response files also remain in the configured server-side upload
directory; activating MySQL does not migrate those files.
