# CLMS Backend

Flask backend for the Computer Laboratory Workspace, Project Repository, and PC Monitoring System.

## Start the server

Run these commands in PowerShell from the repository root. Python 3.9+ and MySQL or MariaDB are required. The repository has no dependency manifest or production server configuration.

1. Create a virtual environment and install the imported packages:

   ```powershell
   python -m venv backend/.venv
   .\backend\.venv\Scripts\python.exe -m pip install Flask python-dotenv PyMySQL PyJWT
   ```

2. Create a database using your MySQL client, then run [Database_Design_V04.sql](backend/database/Database_Design_V04.sql) against it. Insert one row for each `tblRoles.role_name`: `Admin`, `Student`, and `Instructor`. The schema does not seed these roles. This SQL file is present in the current workspace but ignored by Git, so a new checkout needs a copy of it.

3. Copy the environment template and set every value in `backend/.env` using `KEY=value` syntax:

   ```powershell
   if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
   ```

   Required names are `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES`, and `WORKSTATION_API_KEY`. `DB_PORT` and `JWT_ACCESS_TOKEN_EXPIRES` are integers. Use separate random secrets of at least 32 characters for the JWT and workstation keys. Workstation login returns `503` until its key is configured; authentication returns `503` if the JWT key is too short.

4. If the database has no administrator, create the first one with the bootstrap script. It prompts for the password without echo:

   ```powershell
   .\backend\.venv\Scripts\python.exe create_user.py admin-001 First Last admin@example.com admin
   ```

5. Start the development server:

   ```powershell
   .\backend\.venv\Scripts\python.exe run.py
   ```

   `run.py` starts Flask at `http://127.0.0.1:5000` with debug mode disabled. Set `FLASK_DEBUG=1` only for local debugging. No production server command is defined in this repository.

For student workstation login, RFID scanning, logout, and session recovery, see [Workstation and RFID API](backend/WORKSTATION_API.md).

For activity file submissions, resubmission versions, and file access, see [Activity Submissions API](backend/ACTIVITY_SUBMISSIONS_API.md). Run its database migration after the base schema.

For laboratory/hardware management, per-PC agent credentials, monitoring configuration, and snapshot uploads, see [Monitoring API](backend/MONITORING_API.md). Copy the proposed timing values from `.env.example` and provision unique agent credentials before enabling monitoring. Review the [backend monitoring audit](backend/MONITORING_AUDIT.md) for test results and integration limitations.

## Project Structure

```text
clms-backend/
|-- README.md                          Setup and project map
|-- create_user.py                     Interactive first administrator bootstrap
|-- run.py                             Flask development entry point
|-- tests/                             Disposable V04 database integration tests
`-- backend/
    |-- .env.example                   Environment variable names
    |-- __init__.py                    App factory and blueprint registration
    |-- WORKSTATION_API.md             Desktop client API contract
    |-- MONITORING_API.md              Proposed agent and monitoring API contract
    |-- MONITORING_AUDIT.md            Implementation review and verification results
    |-- config/settings.py             JWT settings
    |-- controllers/                   Request validation and API responses
    |-- database/
    |   |-- connection.py              PyMySQL connection settings
    |   |-- Database_Design_V04.sql    Authoritative table definitions
    |   `-- views.sql                  Local SQL views (ignored by Git)
    |-- repositories/                  Parameterized database operations
    |-- routes/                        Flask URL and permission declarations
    |-- services/                      Authentication and business rules
    `-- utils/                         JWT, response, and error helpers
```

Accounts, RFID cards, and laboratory sessions follow the same controller, service, repository, and route layout as the existing modules. The relevant files use `users`, `students`, `instructors`, `auth`, `rfid`, `account`, and `laboratory_sessions` in their names.
