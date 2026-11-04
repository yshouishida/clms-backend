# CLMS backend: API testing and live demonstration

Code review date: **14 October 2026**. Audience: a developer preparing a Project Manager demonstration using Postman or Thunder Client.

## Start here

This guide covers accounts/authentication, RFID, laboratory sessions, laboratories, workstations, hardware, agents, monitoring, snapshots and reports. It uses the current Flask routes and V04 schema. Classes, activities and project repositories are separate modules and are not part of this demonstration.

Use these files together:

| File | Purpose |
|---|---|
| **This guide** | Setup, variables, correct execution order, live script and troubleshooting |
| [Endpoint tests](demo/ENDPOINT_TESTS.md) | 111 named tests, each with the requested nine-step method/URL/auth/headers/body/send/response/verification/troubleshooting structure |
| [Postman collection](demo/CLMS.postman_collection.json) | The same requests, saved and grouped; scripts capture returned IDs/tokens |
| [Empty local environment template](demo/CLMS.postman_environment.json) | Variable names without credentials or invented record IDs |
| [Valid sample PNG](demo/sample-login.png) | Synthetic 64×64 RGB checkerboard, compatible with the upload validator |
| [Invalid image fixture](demo/not-an-image.txt) | Deliberately invalid file for the 415 test |
| [Monitoring contract](../backend/MONITORING_API.md) | Detailed monitoring rules and proposed C# contract |
| [Implementation audit](../backend/MONITORING_AUDIT.md) | Earlier implementation findings and regression-test evidence |

**Do not run the entire collection with Runner.** Some requests are alternatives, require a server restart/manual wait/file selection, intentionally fail, or disable accounts. Follow the numbered rehearsal path below; use optional tests when their prerequisites are satisfied.

### What was actually checked

- Current source routes, controllers, services, repositories, JWT/role decorators, startup/configuration, V04 relationships and sample SQL views were inspected.
- Every request method/path in the collection was matched against the current Flask route map. Every route/method in the seven relevant blueprints is represented.
- The sample PNG was executed through the backend's actual image validator.
- A read-only check reached **MariaDB 10.4.32**, with 27 tables in the configured database. This proves connectivity at the review time, not that your server will always be running.
- Current runtime monitoring timing was **unset** and the agent-key mapping **empty**. Therefore agent/timing-dependent endpoints need configuration before this live demo; the template values are not your current runtime values.
- The earlier saved integration result is 36 passing tests (25 monitoring + 11 account/RFID/session tests). This is prior automated backend evidence, not a claim that Postman, Thunder or physical devices were tested.
- See [request verification results](demo/VERIFICATION.md) for the separate replay of the actual requests supplied with this guide.

## 1. Prepare the environment

### 1.1 Software and terminal location

Use Windows PowerShell, Python (3.12 was used for verification), MySQL/MariaDB, and Postman Desktop or the Thunder Client VS Code extension. This checkout has XAMPP MariaDB tools at `C:\xampp\mysql\bin`. If your installation differs, substitute its actual executable path.

Open a PowerShell terminal in VS Code or Windows Terminal:

```powershell
Set-Location 'C:\Users\ricken\OneDrive\Documents\clms-backend'
python --version
git status --short
```

Stay at this repository root for all Python commands. Leave your existing working changes intact.

### 1.2 Virtual environment and packages

If `backend/.venv` already exists, reuse it. Otherwise:

```powershell
python -m venv backend/.venv
```

Activate it:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m pip install Flask python-dotenv PyMySQL PyJWT
```

There is no `requirements.txt` or `pyproject.toml` dependency manifest in the inspected checkout; do not run an invented `pip install -r requirements.txt`. Werkzeug is installed as a Flask dependency. No Pillow dependency is required for the supplied PNG fixture.

If PowerShell blocks activation, use the interpreter directly instead of changing system execution policy:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install Flask python-dotenv PyMySQL PyJWT
```

In later commands, replace `python` with `.\backend\.venv\Scripts\python.exe` if you did not activate. Confirm the environment:

```powershell
python -c "import sys, flask, pymysql, jwt, dotenv; print(sys.executable); print('Imports OK')"
```

### 1.3 Start/select the database

In XAMPP Control Panel, start **MySQL** (XAMPP uses MariaDB here). Do not launch a second server on an already occupied port. Choose an approved **demo database**, preferably separate from real student records. Back up an existing database through your database administration tool before modifying it.

Open its SQL console; for XAMPP's client, replace `YOUR_DB_USER` with your actual database username and use the configured database port:

```powershell
& 'C:\xampp\mysql\bin\mysql.exe' -h 127.0.0.1 -P 3306 -u YOUR_DB_USER -p
```

The password is prompted. Port 3306 here is the template example; use your actual `DB_PORT`. For an existing database, select its actual name and inspect it. For a **new empty demo database only**, execute:

```sql
CREATE DATABASE clms_demo CHARACTER SET utf8mb4;
USE clms_demo;
SOURCE C:/Users/ricken/OneDrive/Documents/clms-backend/backend/database/Database_Design_V04.sql;
```

Do not import V04 over existing tables: it contains plain CREATE TABLE statements, not an upgrade migration. This guide does not delete/drop an existing database. The optional `views.sql` can be sourced after the schema; the new API uses base tables and does not require those views to start.

Check the selected database and required relationships:

```sql
SELECT DATABASE(), VERSION();
SHOW TABLES;
SHOW CREATE TABLE tblWorkstations;
SHOW CREATE TABLE tblLaboratorySessions;
SHOW CREATE TABLE tblCameraCaptures;
SELECT id, role_name FROM tblRoles ORDER BY id;
```

At minimum, verify `tblRoles`, `tblUsers`, `tblStudents`, `tblInstructors`, `tblRFIDCards`, `tblRFIDAssignments`, `tblLaboratories`, `tblWorkstations`, `tblRFIDReaders`, `tblArduinoDevices`, `tblCameras`, `tblLaboratorySessions`, `tblCameraCaptures`, `tblPCStatus`, `tblSystemLogs`, and `tblAuditLogs` exist. Use the full V04 schema rather than manually creating only this subset.

V04 does not seed roles. If a role is missing, insert only that missing name:

```sql
INSERT INTO tblRoles (role_name)
SELECT 'Admin' WHERE NOT EXISTS (SELECT 1 FROM tblRoles WHERE role_name = 'Admin');
INSERT INTO tblRoles (role_name)
SELECT 'Student' WHERE NOT EXISTS (SELECT 1 FROM tblRoles WHERE role_name = 'Student');
INSERT INTO tblRoles (role_name)
SELECT 'Instructor' WHERE NOT EXISTS (SELECT 1 FROM tblRoles WHERE role_name = 'Instructor');
SELECT id, role_name FROM tblRoles ORDER BY id;
```

Write down the actual Student and Instructor role IDs. **There is no role-list API. Do not assume 1/2/3.** V04 does not uniquely constrain role_name; if duplicate role rows already exist, have the database owner review them rather than silently renumbering records.

### 1.4 Configure private backend environment

From the repository root:

```powershell
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
notepad backend\.env
```

Fill the actual `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Use your demo DB name, not necessarily the template `clms`. Also configure:

```dotenv
JWT_SECRET_KEY=<your separate random JWT secret>
JWT_ACCESS_TOKEN_EXPIRES=3600
WORKSTATION_API_KEY=<your separate random workstation login key>
MONITORING_HEARTBEAT_INTERVAL_SECONDS=30
MONITORING_OFFLINE_AFTER_SECONDS=120
MONITORING_MAX_CLOCK_SKEW_SECONDS=5
WORKSTATION_AGENT_KEY_HASHES={}
REGISTRATION_DEVICE_IDS={}
```

Angle-bracket text is a placeholder, not a valid credential to reuse. Generate distinct random values locally when needed:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

JWT and workstation keys must each contain at least 32 characters. Keep output/private `.env` off screenshots, Git and shared collection exports. Do not change the JWT key between login and later requests. Existing OS environment values take precedence over `.env` because `load_dotenv` does not override them by default; inspect your terminal environment if edits seem ignored.

The 30/120/5 timings are **proposed configurable demo values** already present in `.env.example`; no such values were loaded during the initial check. Later, verify the real values with AGENT-CONFIG. Agent credentials are configured after obtaining a real workstation ID in section 5.

Test the application's configured database connection without printing secrets:

```powershell
python -c "from backend.database.connection import get_connection; c=get_connection(); q=c.cursor(); q.execute('SELECT DATABASE() AS db, VERSION() AS version'); print(q.fetchone()); q.execute('SHOW TABLES'); print('Tables:',len(q.fetchall())); q.close(); c.close()"
```

Expected: your intended demo database and version, followed by a table count. A successful Flask startup by itself does not prove database connectivity.

### 1.5 Obtain an administrator safely

There are no guaranteed default demo credentials. Test fixture accounts live in temporary databases and are not seeded into your demo database. Use credentials supplied by the account owner, or bootstrap a new administrator on an approved demo database.

**Current source warning:** `create_user.py` hardcodes an account/password, assumes role ID 1, ignores command-line arguments, and executes on import. Do not run it as an interactive bootstrap or use its weak fixed credential for the demo. This guide leaves application code unchanged.

If the demo database needs its first Admin, seed the Admin role as above, then run this local command. It calls the existing `create_admin_service`, validates fields, hashes the password, and resolves the Admin role by name:

```powershell
python -c "from getpass import getpass; from backend.services.account_service import create_admin_service; fields=('account_id','first_name','last_name','email','username'); body={key:input(key+': ').strip() for key in fields}; body['password']=getpass('Password (at least 8 characters): '); print(create_admin_service(body))"
```

Choose unique values and remember the username/password privately. Output includes `user_id` and `role_name=Admin`; it does not return the password. This is a trusted local database setup operation, not an unauthenticated HTTP registration endpoint. If duplicates exist, use a different demo account or ask its owner; do not overwrite passwords silently.

### 1.6 Start Flask

```powershell
python run.py
```

`run.py` creates the app and calls `app.run(debug=os.getenv('FLASK_DEBUG') == '1')`. It supplies no host/port override; inspected Flask defaults are localhost and port **5000**. Expected terminal message: `Running on http://127.0.0.1:5000`. Use the URL actually printed in your terminal. Keep this terminal running; Ctrl+C stops it.

If port 5000 is occupied, stop your earlier server or explicitly choose a separate port using the real factory:

```powershell
python -m flask --app 'backend:create_app()' run --host 127.0.0.1 --port 5001
```

Then set `base_url` to `http://127.0.0.1:5001`. This is a development-only alternative, not a configured production deployment.

To verify HTTP reachability in Postman: send `GET {{base_url}}/admins` with **No Auth**. Expected `401` and `Authorization is required.` This proves Flask routing is alive; subsequent successful login/reads prove database integration. There is no `/health`, `/api`, `/me` or `/agent/login` route in this scope. A browser GET `/` or GET `/login` can return 404/405 even when Flask is working correctly.

## 2. Configure Postman or Thunder Client

### 2.1 Postman: import the prepared requests

1. Open Postman Desktop. Use a private/local workspace for demonstration credentials.
2. Click **Import**, select `docs/demo/CLMS.postman_collection.json`, then import the environment JSON.
3. Select **CLMS Demo - LOCAL VALUES ONLY** in the environment selector.
4. Open the environment editor. Fill only the required private inputs described below. Keep unset IDs blank until obtained from responses.
5. Open the collection. Folders 01–08 contain the core flow; 09–11 contain optional RFID, negative and account-maintenance tests.
6. Open a request and check its HTTP method and URL at the top. `{{base_url}}` resolves from the active environment.
7. In **Authorization**, choose **Bearer Token** and enter the relevant `{{..._token}}` variable. Imported requests already set this. Do not also create a duplicate Authorization header.
8. In **Headers**, JSON writes use `Content-Type: application/json`. Workstation logins use `X-Workstation-Key`, not a human JWT or agent key.
9. In **Body**, choose **raw → JSON** for JSON requests, **none** for GET/bodyless actions, or **form-data** for snapshots.
10. Click **Send**. Read the HTTP status, then JSON Body. Check **Test Results** for the collection's status/envelope assertions. A 401/403/409 is a passing *negative* test only when that request expects it.
11. Click **Save** after intentional changes. Preserve valid requests; duplicate a request before changing it into a negative test.

For manual creation, select **Collections → New collection**, name it `CLMS Demo`, add an HTTP request, choose its method, paste its URL and follow the nine steps in the endpoint reference. Collections organize and save requests; see [official Postman collection instructions](https://learning.postman.com/docs/use/use-collections/create-collections).

The collection's pre-request script refreshes `observed_at` to `new Date().toISOString()` on every send. Post-response scripts save successful IDs/tokens into the selected environment. Variable syntax and scopes are documented in [Postman's variable guide](https://learning.postman.com/latest-v-12/docs/use/send-requests/variables/define-variables). Inspect any red/unresolved variable before sending. Do not export the filled environment or share its secrets.

### 2.2 Thunder Client: equivalent manual workflow

1. In VS Code, open the Thunder Client sidebar. In **Collections**, create a collection named `CLMS Demo` using its menu.
2. Open **Env**, create/select a demo environment, and add variables using the table below. Use local secret storage if available.
3. Click **New Request**. Choose GET/POST/PATCH/PUT/DELETE from the method selector and paste the exact URL from the endpoint tests.
4. Choose **Auth → Bearer** for human/agent tokens. For workstation login choose No Auth and add `X-Workstation-Key` under Headers.
5. Use **Body → JSON** for JSON requests; for uploads use the Form body editor and select the file type for `image`.
6. Click **Send**, compare status/body, then save the request into the collection with the named test code.
7. Copy tokens and IDs from response fields into the environment manually. Replace `observed_at` before every timestamped request. Generate a UTC value with `[DateTime]::UtcNow.ToString('o')` in PowerShell.

Thunder supports `{{variable}}` and local environments for secrets; see [official environment documentation](https://docs.thunderclient.com/features/environments). Its current [import documentation](https://docs.thunderclient.com/features/import) lists Postman 2.1 imports as a paid feature. If your edition permits, use Collection menu → Import. Do not assume imported Postman JavaScript runs unchanged in Thunder: use manual variable copying or adapt it using [Thunder's Postman script conversion reference](https://docs.thunderclient.com/scripting/postman). The manual workflow requires no imported script execution.

### 2.3 Variables: where each value comes from

| Variable | Source / meaning |
|---|---|
| `base_url` | Flask's printed origin, normally `http://127.0.0.1:5000`, no trailing slash |
| `admin_username`, `admin_password` | Actual existing/bootstrapped administrator credentials |
| `instructor_username`, `instructor_password` | Chosen credentials used in ACCOUNT-INSTRUCTOR, or an approved existing account |
| `student_username`, `student_password` | Chosen credentials used in ACCOUNT-STUDENT, or approved existing account |
| `other_student_username`, `other_student_password` | A second demo student for conflict/ownership tests |
| `demo_suffix` | Your short unique demo label, at most 10 characters, e.g. locally generated timestamp; not a database ID |
| `student_role_id`, `instructor_role_id` | Actual `SELECT id, role_name FROM tblRoles` result; keep numbers unquoted in JSON |
| `admin_token`, `instructor_token`, `student_token`, `other_student_token` | **Top-level `access_token`** from each role's ordinary POST `/login` |
| `admin_user_id`, `student_user_id`, `other_student_user_id` | Top-level login `id` or creation `data.user_id` from tblUsers |
| `student_id`, `other_student_id` | Login `student_id`, creation `data.student_id`, or selected student list `data[i].student_id` from tblStudents |
| `instructor_id` | Creation `data.instructor_id` or selected instructor list record; ordinary login does not return it |
| `laboratory_id`, `workstation_id` | Creation `data.id` or the ID of an intentionally selected existing inventory record |
| `reader_id`, `arduino_id`, `camera_id` | Hardware creation `data.id`, selected inventory record, or AGENT-CONFIG `data.devices` |
| `registration_reader_id`, `registration_arduino_id` | Registration hardware POST response IDs, with null workstation assignment |
| `workstation_key` | Your private `.env` WORKSTATION_API_KEY; used in X-Workstation-Key |
| `agent_token` | Raw per-PC random secret you generate in section 5; **not a JWT and not the SHA-256 digest** |
| `devices_json` | JSON array of every Active device from AGENT-CONFIG; choose Connected/Disconnected explicitly for simulation |
| `observed_at` | Fresh ISO-8601 UTC timestamp; Postman pre-request script supplies it |
| `heartbeat_interval`, `offline_after` | Actual AGENT-CONFIG timing fields saved by its script |
| `workstation_student_token` | Workstation login **`data.access_token`**, containing the session ID |
| `session_id` | Workstation login **`data.session.session_id`** |
| `capture_id`, `failed_capture_id` | Upload/failure **`data.capture_id`**; keep these separate |
| `card_uid`, `new_card_uid` | Unique demo strings you deliberately register, or actual approved reader UIDs; not pre-existing credentials supplied by this guide |
| `card_id`, `new_card_id` | Card registration **`data.card_id`**; list responses use `id` |
| `other_workstation_id`, `other_camera_id` | Actual alternate inventory records for mismatch tests; leave blank and skip if unavailable |
| `recovery_session_id` | Actual abandoned **demo** session selected for optional admin termination |
| `extra_admin_username/password/user_id` | Optional additional Admin creation inputs/returned ID; unnecessary for the core demo |

Numeric variables in raw JSON must resolve without quotes: `"workstation_id": {{workstation_id}}`. Text values use quotes. `"devices": {{devices_json}}` is a real JSON array, not a quoted JSON string. A blank variable makes invalid JSON; fill it or skip that test. Choose passwords locally (at least 8 characters); generated URL-safe strings avoid JSON quote-escaping problems.

Ordinary login token-saving example (Postman **Scripts → Post-response**):

```javascript
if (pm.response.code === 200) {
  const body = pm.response.json();
  pm.environment.set("admin_token", body.access_token);
  pm.environment.set("admin_user_id", body.id);
}
```

Workstation login is different:

```javascript
if (pm.response.code === 201) {
  const body = pm.response.json();
  pm.environment.set("workstation_student_token", body.data.access_token);
  pm.environment.set("session_id", body.data.session.session_id);
}
```

### 2.4 Read responses correctly

Most endpoints return:

```json
{"success":true,"message":"<operation message>","data":null}
```

`data` is replaced by the actual record/array for reads and creates; logout returns null. Expected error envelope:

```json
{"success":false,"message":"<reason>","error":null}
```

Important exceptions: `/login` returns a **flat** token/user object; successful image downloads return **binary PNG**. Flask routing errors can be HTML. The endpoint reference gives exact success messages, expected statuses and result types without fabricating record IDs or timestamps.

For example, the **shape** of a successful workstation login is below. Angle-bracket values stand for actual response values; do not paste this response template as a request or expect literal strings for numeric IDs. The `user` object includes additional public identity/profile fields returned by the implementation.

```text
{
  "success": true,
  "message": "Student workstation login succeeded.",
  "data": {
    "access_token": "<workstation student JWT>",
    "user": { <public student identity fields> },
    "session": {
      "session_id": <returned integer>,
      "student_id": <actual student profile integer>,
      "workstation_id": <actual workstation integer>,
      "rfid_id": null,
      "login_method": "Manual",
      "status": "Active"
    }
  }
}
```

Other useful result keys, all inside `data` unless explicitly stated:

| Operation | Returned structure to inspect |
|---|---|
| Ordinary login | Top-level access_token/id/account_id/name/email/username/status/role_name/student_id/student_number/program/year_level/section/employee_number; nullable profile fields depend on role |
| Student / Instructor create | user_id plus student_id / instructor_id |
| Admin create/update | user_id, role_name |
| Account status | user_id, status |
| Inventory create/get/update | id and the resource's schema fields; hardware additionally has assignment |
| Heartbeat | pc_status_id, duplicate |
| Snapshot upload/failure | capture_id, capture_status, duplicate |
| Capture metadata | id, session_id, camera_id, captured_at, capture_status, workstation_id, student_id; no file_path |
| Session-specific logout/termination | session_id, status, already_finished |
| Legacy session heartbeat | session_id, pc_status_id |
| Agent error | system_log_id, duplicate |
| RFID register | card_id, card_uid, status |
| RFID assign / replace | assignment_id, student_id, card_id (assign), or old_card_id/new_card_id (replace) |
| Capture summary row | workstation_id, camera_id, capture_status, capture_count |

## 3. Authenticate and prove role boundaries

Use the test codes in [Endpoint tests](demo/ENDPOINT_TESTS.md); the same code appears in the collection.

1. **AUTH-ADMIN**: send actual admin credentials. Expect 200; save top-level token/id. **AUTH-ME** verifies returned account/role, and **AUTH-ADMINS** proves Admin access.
2. If approved accounts already exist, use them. Otherwise run **ACCOUNT-INSTRUCTOR**, **ACCOUNT-STUDENT**, **ACCOUNT-OTHER** using actual role IDs and your chosen credentials. Do not create them again on every rehearsal; duplicate account fields return 409.
3. Run **AUTH-INSTRUCTOR**, then **DASHBOARD-INSTRUCTOR** or **LAB-LIST** with instructor_token. Read access is allowed. **NEG-INSTRUCTOR** calls `/admins` with that token and must return 403.
4. Run **AUTH-STUDENT** and **AUTH-OTHER_STUDENT**. **SESSION-OWN** is an authorized Student read. **NEG-STUDENT** proves Students cannot read inventory.
5. Compare **ACTIVE-BEFORE** before and after ordinary role logins. No session must be added. A normal Student `/login` also creates no workstation session.
6. Try **NEG-PASSWORD**, **NEG-NO-TOKEN**, **NEG-BAD-JWT**. Enter a deliberately different `invalid_password`; keep your real stored password unchanged.
7. Optional disabled-account demonstration: get other_student_token first, then **ACCOUNT-DISABLE → ACCOUNT-DISABLED-LOGIN → ACCOUNT-DISABLED-TOKEN → ACCOUNT-ACTIVATE → AUTH-OTHER_STUDENT**. Use `other_student_user_id`, not its profile ID. Disabling terminates that student's active sessions; use the secondary account before it occupies a PC.

There is no separate Admin, Instructor or Student login URL. The stored role decides permissions. Instructor and Admin dashboard login must never be replaced with a student workstation login request.

## 4. Inventory and hardware rehearsal

### 4.1 Laboratory and PC records

Run **LAB-LIST** and **PC-LIST** first. If the real 37 PCs are already registered, select an approved idle PC and its lab, copy actual IDs, and skip creation. A duplicate list must not be seeded to make a count look correct.

For an empty approved demo database: **LAB-CREATE → LAB-GET → LAB-UPDATE → PC-CREATE → PC-GET → PC-LAB → PC-UPDATE → PC-ASSIGN**. These create one sample PC. Say “one synthetic demo PC” rather than claiming all 37 have been deployed. If inventory genuinely needs 37 records, register each actual PC once with its real unique PC name/asset tag; that is deployment preparation, not this live script.

**NEG-PC-DUP** repeats the just-created identifiers and expects 409. When reusing existing inventory, edit this test to its actual pc_name/asset_tag first. **NEG-PC-INVALID** intentionally sends laboratory_id=0 and expects 400. For missing-reference 404, use a positive ID that you have verified is absent in your test database, rather than guessing an existing record.

### 4.2 Selected workstation hardware

Before creating any student session, run LIST/GET requests for `rfid-readers`, `arduinos`, `cameras`. Reuse the selected PC's real assigned devices. If absent in a demo DB, run each **CREATE** request once. The `serial_port: COM3` example is an inventory value only; it is not proof that a physical port exists.

The **UPDATE**, **ASSIGN**, and **BY-PC** requests show readable device metadata and assignment validation. Moves require idle source/target PCs, no conflicting Active same-kind device, and reset availability to Disconnected. Cameras require a workstation ID; reader/Arduino records may be unassigned. **NEG-HARDWARE** proves a second Active camera cannot occupy the same PC assignment. Run it before starting a session so it specifically tests assignment conflict.

To identify the five equipped PCs, read all three device inventories and the dashboard: `with_rfid`, `with_camera`, `with_arduino` count Active device capabilities. These counts should be five only if five actual sets are registered. A PC with only a reader does not become a camera-equipped PC.

### 4.3 Registration station pair

Use existing registration devices if present. Otherwise run **rfid-readers-REG** and **arduinos-REG**, with `workstation_id: null`. Save their IDs, then edit the private backend `.env`:

```dotenv
REGISTRATION_DEVICE_IDS={"rfid-readers":<actual registration reader ID>,"arduinos":<actual registration Arduino ID>}
```

Replace placeholders with integers; the final value must be valid JSON. Restart Flask. Read `/hardware/rfid-readers/<actual ID>` and `/hardware/arduinos/<actual ID>` with Admin: `assignment` should be `Registration Station`, workstation_id remains null. No API endpoint creates a separate registration-station entity or configures this mapping. No fake 38th laboratory workstation is needed.

Hardware API registration proves database records and relationship checks only. Real reader scanning, Arduino firmware, camera availability and serial communication remain desktop/embedded-team integration tests.

## 5. Provision and authenticate a workstation agent

Obtain the chosen **actual workstation_id** before this step. Generate a new secret locally:

```powershell
python -c "import secrets, hashlib; key=secrets.token_urlsafe(32); print('RAW AGENT KEY (private):',key); print('SERVER SHA256:',hashlib.sha256(key.encode()).hexdigest())"
```

Put the raw value into local API-client `agent_token`. Put only its 64-character lowercase digest into private `.env`, keyed by the actual workstation ID:

```dotenv
WORKSTATION_AGENT_KEY_HASHES={"<actual workstation ID>":"<its SHA256 digest>"}
```

Both placeholders must be replaced. JSON keys are quoted strings; digests are quoted strings. Add unique keys/digests for additional PCs; do not reuse a key. Keep any existing valid mappings when adding a demo PC. Restart Flask to load changes, then refresh logins if needed.

Send **AGENT-CONFIG** with `Authorization: Bearer {{agent_token}}`. Expected 200. This is the authentication demonstration—**there is no agent login/token-minting endpoint**. Read the returned workstation identity, device IDs, reporting interval, offline timeout and snapshot limits.

**NEG-AGENT**, **NEG-HUMAN-AGENT** and **NEG-OTHER-PC** demonstrate wrong key, human JWT substitution and workstation impersonation rejection. Configure the server first; otherwise 503 means “not configured,” not “wrong credentials rejected.”

AGENT-CONFIG's Postman script deliberately prepares `devices_json` with **Connected** for each assigned Active device. This is a clearly labelled simulation. In Thunder, copy `data.devices`, retaining each kind/id and setting the desired simulated connection status. Never omit a disconnected assigned device. A PC with no Active hardware uses `[]`.

## 6. Monitoring, stale detection and dashboard

1. Send **HEARTBEAT**. The request includes all CPU/RAM/storage percentages and network/device statuses together. No separate CPU or RAM endpoint exists.
2. Expect 201 (new row), or 200 for an identical same-second retry. Send changed samples at least one second apart.
3. Read **DASHBOARD**, **DASHBOARD-LAB** and **MONITOR-HISTORY**. Locate the actual workstation_id; confirm the submitted percentages, last_heartbeat_at and online=true. Values you typed are simulated measurements.
4. For disconnected hardware, edit only the appropriate entry in `devices_json` to Disconnected, keep every other assigned entry, send a fresh heartbeat, then inspect that hardware record and hardware_unavailable. Restore Connected and send another fresh sample before snapshot testing.
5. **NEG-METRIC** sends CPU=101 and must reject without adding a record. Other optional variations: negative RAM, boolean storage_usage, unknown network status, missing device, or old/future timestamp.

### 6.1 Stale heartbeat demonstration

Use **actual `data.offline_after_seconds` from AGENT-CONFIG**; with the proposed demo config it will be 120. Do not merely assume the server loaded the template.

1. Send a fresh HEARTBEAT; read dashboard and show online=true.
2. Stop sending agent heartbeats. Stop any collection runner or real C# agent reporting for this demo PC.
3. Wait **offline_after + 2 seconds** from the last accepted sample (122 seconds for a confirmed 120-second configuration). Dashboard reads do not refresh heartbeat time. You can explain permissions/reports during the wait.
4. Read dashboard again: this PC should show online=false, connectivity_reason=Stale, with the old last_heartbeat_at retained. No scheduled cleanup worker is required; freshness is calculated on read.
5. Send HEARTBEAT again with a fresh timestamp; read dashboard and show online=true. This demonstrates reconnection.

An offline PC's Active student session remains Active. Optional proof: repeat the wait after SESSION-LOGIN, then compare SESSION-ACTIVE before/after. `in_use` may remain true while `online` is false. This is intentional; a network interruption is not a student logout.

### 6.2 Explain dashboard counts

| Field | Meaning |
|---|---|
| total | Actual registered PC rows (including maintenance/retired records), not a hardcoded 37 |
| online / offline | Fresh Online sample versus no fresh Online sample; online + offline = total |
| in_use | PCs with at least one Active session, independently of connectivity |
| available | Online + no Active session + Active/Working PC + Active lab |
| with_rfid / with_camera / with_arduino | PCs with Active assigned devices of the relevant kind |
| hardware_unavailable | PCs with unavailable device records or offline PCs with active hardware |

`online - in_use` is not necessarily `available`: some occupied PCs may be offline and some online PCs may be under maintenance. Admin sees current_student only when exactly one active session exists. Instructor dashboard omits that identity. Use the API's computed values rather than inventing client-side count rules.

## 7. Connect student login to a workstation session

Run these after inventory/agent setup and before snapshot tests:

1. **ACTIVE-BEFORE**: note current sessions; confirm selected PC and student are free.
2. **SESSION-LOGIN**: uses X-Workstation-Key, student credentials and workstation_id. Expect 201, correct IDs, Manual and Active.
3. Save `workstation_student_token` separately from ordinary student_token; save session_id from data.session.
4. **SESSION-ACTIVE**, **SESSION-OWN**, **DASHBOARD**: show student/PC association, in_use=true and available=false. Admin/Instructor dashboard authentication alone did not create this row.
5. **SESSION-CONFLICT**: another valid student's credentials on the occupied PC must return 409. The existing session remains the only new one.
6. **HEARTBEAT-SESSION**: submit agent metrics linked to session_id. **SESSION-HEARTBEAT** is a separate legacy Student JWT heartbeat; it cannot establish trusted agent connectivity.
7. **NEG-SESSION-OWNER**: other_student_token cannot complete this session (403).
8. Complete snapshot tests in section 8 while the session remains Active.
9. **SESSION-LOGOUT**: POST /logout with the workstation_student_token completes its session and revokes that token. An ordinary dashboard token would only log out that token, not end the workstation session.
10. **SESSION-REPEAT** with Admin safely returns already_finished=true. Repeating `/logout` with its revoked JWT instead returns 401. These are different operations.
11. **SESSION-AFTER**: Completed and logout_at should be visible. Send HEARTBEAT **without session_id** (or with null) to refresh connectivity; completed-session association would return 409. Dashboard becomes available only if the other availability rules hold.

There is no generic unauthenticated “create session” endpoint. Session creation occurs through the verified manual/RFID workstation login flows. Recovery is Admin review via SESSION-RECOVERY and optional SESSION-TERMINATE; it is not automatic offline completion.

## 8. Upload and retrieve a camera snapshot

Use the supplied synthetic checkerboard PNG to avoid relying on a physical webcam. It is 8-bit, non-interlaced RGB and passes the current validator. Arbitrary PNG exports can be indexed/grayscale/interlaced and are not necessarily accepted. JPEG is not accepted by the implemented contract.

1. Keep the student's session Active. Verify camera_id belongs to this same PC and its status is Active.
2. Send a fresh agent heartbeat reporting this camera Connected.
3. Open **CAPTURE-UPLOAD**. Authentication is the PC's agent key, not student_token.
4. In Body choose form-data/Form. Add exactly these fields:

   | Key | Type | Value |
   |---|---|---|
   | session_id | Text | `{{session_id}}` |
   | camera_id | Text | `{{camera_id}}` |
   | captured_at | Text | `{{observed_at}}` freshly generated after login |
   | image | File | Select `docs/demo/sample-login.png` |

5. Remove any manually set JSON Content-Type header. Let the client generate the multipart boundary and Content-Length; do not type a guessed file size.
6. Send. First upload returns 201, data.capture_status=Captured and capture_id. An identical canonical file retry returns 200. There is one successful login snapshot per session/camera; different file contents conflict with 409.
7. **CAPTURE-LIST**, **CAPTURE-DETAIL** verify session/camera/PC/student associations without exposing storage paths.
8. **CAPTURE-DOWNLOAD** with Admin returns PNG bytes. Use Preview, Save response, or download depending on client UI. Expect a private attachment, not a public URL.
9. **CAPTURE-OWN** succeeds for metadata only; **CAPTURE-DENIED** returns 403 even for the owning student's image request. **CAPTURE-OTHER** returns 404 to another Student.
10. Run **NEG-CAPTURE-TYPE**, **NEG-CAPTURE-AUTH**, **NEG-CAPTURE-SESSION**. They prove format/auth/ID rejection. **NEG-CAPTURE-CAMERA** requires an actual alternate-PC camera; skip and mark Not Tested if you do not have one. For a positive-but-nonexistent session test, confirm an absent positive ID using SQL before sending; this returns 409 association failure, whereas zero returns 400 validation failure.
11. **CAPTURE-FAILURE → CAPTURE-FAILED-FILE** proves Failed metadata/logging with no image and no session termination. A Disconnected failure updates camera availability unless a newer sample already exists; send a newer Connected heartbeat to restore your simulation.

Defaults: 5 MiB image, 16,777,216 pixels, bounded multipart overhead. Files reside under private `instance/camera_captures` unless configured otherwise. Do not make that directory publicly served. A DB/file failure must not be presented as success. Long-delayed capture uploads outside the reporting window or after session completion are rejected.

This proves the backend can accept/associate/protect a supplied image. It does not prove webcam capture, C# PNG encoding, Wiegand signals, Arduino serial transport or hardware availability measurements.

## 9. Logs, reports and optional RFID lifecycle

**AGENT-ERROR** records a simulated Arduino error. **SYSTEM-LOGS** finds it by workstation and returned system_log_id; repeating exactly the same error within 60 seconds may return duplicate=true. Allowed components are Agent, Network, Camera, RFID, Arduino. Do not submit passwords or student details in error messages.

Existing report interfaces are inventory lists, per-PC hardware lists, monitoring history, dashboard, session usage summary and capture summary. There is no additional `/reports/...` or PDF/Excel export endpoint. **CAPTURE-SUMMARY** separates Captured/Failed counts; **SESSION-SUMMARY** includes completed/terminated usage duration. **SESSION-RECOVERY** is a review list with minutes=60 by default, separate from monitoring's stale seconds.

Optional RFID demo, after the manual session is completed:

1. Set a unique demo card_uid, then **RFID-LIST → RFID-REGISTER → RFID-ASSIGN → RFID-HISTORY**. Assignment uses student_id from tblStudents.
2. Verify the assigned reader is Active/Connected on the selected PC. Send a fresh agent heartbeat if needed.
3. **RFID-LOGIN** simulates the UID coming from C#. Expect 201 and login_method=RFID. Save its NEW session_id/workstation_student_token; then use SESSION-LOGOUT to finish it.
4. Register new_card_uid with **RFID-NEW**, then **RFID-REPLACE**. History shows old assignment Ended/new assignment Active. Old UID login must fail 401.
5. **RFID-STATUS** deactivates the new card. Login with new_card_uid now fails 401. Reactivating a card does not restore its ended assignment; assign it explicitly again to test future login.
6. Unregistered UID, inactive card and disabled student all fail RFID eligibility. To demonstrate the disabled-student case without disturbing the main demo, finish all sessions, disable that demo student's tblUsers account using the same status route, try its currently Active/assigned card, then reactivate and sign in again. Record which prerequisite caused each rejection.

For explicit card activation, duplicate RFID-STATUS, target the desired actual card ID and use `{"status":"Active"}`. Valid status enums are Active, Inactive, Disabled, Lost, Damaged. All card-management routes require Admin.

## 10. Read-only database checks

Use your database client's SQL console on the selected demo DB. Replace the example SQL session variables with **returned IDs** before executing; the commented assignment is a template, not an instruction to use a fake ID.

```sql
-- SET @demo_pc = <returned workstation_id>;
-- SET @demo_session = <returned session_id>;
SELECT COUNT(*) AS registered_pcs FROM tblWorkstations;
SELECT laboratory_id, COUNT(*) AS pcs FROM tblWorkstations GROUP BY laboratory_id;
SELECT COUNT(DISTINCT workstation_id) AS equipped_readers
FROM tblRFIDReaders WHERE status = 'Active' AND workstation_id IS NOT NULL;
SELECT COUNT(DISTINCT workstation_id) AS equipped_cameras
FROM tblCameras WHERE status = 'Active';
SELECT COUNT(DISTINCT workstation_id) AS equipped_arduinos
FROM tblArduinoDevices WHERE status = 'Active' AND workstation_id IS NOT NULL;
SELECT COUNT(DISTINCT workstation_id) AS occupied_pcs
FROM tblLaboratorySessions WHERE status = 'Active';

SELECT id, student_id, workstation_id, login_method, login_at, logout_at, status
FROM tblLaboratorySessions WHERE id = @demo_session;
SELECT id, workstation_id, session_id, online_status, cpu_usage, ram_usage,
       storage_usage, network_status, camera_status, rfid_status, recorded_at
FROM tblPCStatus WHERE workstation_id = @demo_pc
ORDER BY recorded_at DESC, id DESC LIMIT 10;
SELECT c.id, c.session_id, c.camera_id, c.capture_status, c.captured_at,
       s.student_id, s.workstation_id
FROM tblCameraCaptures c
JOIN tblLaboratorySessions s ON s.id = c.session_id
WHERE c.session_id = @demo_session;
SELECT id, source, log_level, message, created_at
FROM tblSystemLogs WHERE workstation_id = @demo_pc ORDER BY id DESC LIMIT 20;
```

Do not count `online_status='Online'` over all history rows as the online-PC total. The dashboard selects latest **agent** samples and applies freshness. Legacy session samples have NULL network_status; agent samples require non-NULL. PC status storage follows the existing database-local convention; API monitoring timestamps are UTC. Raw views intentionally do not apply the API's stale policy. Compare counts using the same lab filter/status rules and use Admin dashboard as the authoritative current connectivity output.

## 11. Live presentation script

Prepare accounts, inventory, credentials and file selections **before** the meeting. This live order avoids setup interruptions. Keep the endpoint guide open for full payloads; these are the exact matching collection codes.

| Step | What to say | Request / action | Expected result and proof | Next |
|---|---|---|---|---|
| 1 | “I am starting the existing Flask backend.” | `python run.py` | Printed local URL; startup imports succeed | DB check |
| 2 | “The application reaches our demo database.” | Read-only Python DB check in 1.4 | Intended DB/version/table count | Admin login |
| 3 | “Admin authentication returns a role-bound JWT.” | AUTH-ADMIN | 200; role_name Admin | AUTH-ME |
| 4 | “This protected endpoint permits administrators.” | AUTH-ME, AUTH-ADMINS | Authenticated identity and Admin directory | Baseline sessions |
| 5 | “Dashboard login does not create a student session.” | ACTIVE-BEFORE | Record baseline session IDs | Instructor login |
| 6 | “Instructors can read monitoring, but cannot administer accounts.” | AUTH-INSTRUCTOR, DASHBOARD-INSTRUCTOR, NEG-INSTRUCTOR | 200 read, 403 Admin list | Student login |
| 7 | “Students can read their own history.” | AUTH-STUDENT, SESSION-OWN, NEG-STUDENT | 200 own history, 403 inventory | Compare sessions |
| 8 | “These dashboard logins added no laboratory sessions.” | SESSION-ACTIVE | Same IDs/count as baseline | Inventory |
| 9 | “Every PC belongs to a laboratory.” | LAB-LIST, PC-LAB, PC-GET | Actual records and lab links | Hardware |
| 10 | “Only selected PCs have these hardware sets.” | Three hardware BY-PC requests | Real assignments; no assumption all 37 are equipped | Agent auth |
| 11 | “This credential identifies one workstation, separately from users.” | AGENT-CONFIG, NEG-HUMAN-AGENT | Own key 200, Admin JWT 401 | Heartbeat |
| 12 | “Postman is simulating the C# agent.” | HEARTBEAT | 201 with pc_status_id; sample metrics stored | Dashboard |
| 13 | “The dashboard reflects the accepted sample.” | DASHBOARD, MONITOR-HISTORY | Online, matching metrics/time; explain simulated values | Stop reporting |
| 14 | “We now stop heartbeats to simulate lost connectivity.” | No more agent sends; wait actual offline_after+2 seconds | No request mutates session state | Explain reports during wait |
| 15 | “The timeout marks stale connectivity, not logout.” | DASHBOARD | This PC offline/Stale | Reconnect |
| 16 | “A fresh report restores connectivity.” | HEARTBEAT, DASHBOARD-LAB | Online again; consistent scoped counts | Workstation login |
| 17 | “A student workstation login creates the session.” | SESSION-LOGIN | 201; correct student/PC and Active status | Occupancy |
| 18 | “Session occupancy is independent of network state.” | SESSION-ACTIVE, DASHBOARD | in_use true, available false | Conflict test |
| 19 | “Another student cannot occupy this PC simultaneously.” | AUTH-OTHER_STUDENT, SESSION-CONFLICT | 409; no duplicate session | Associated metrics |
| 20 | “Agent metrics may reference this active session.” | HEARTBEAT-SESSION | Correct active session accepted | Snapshot |
| 21 | “This sample image tests backend snapshot handling.” | CAPTURE-UPLOAD | Captured ID; linked to session/camera/PC | Retrieval |
| 22 | “Only an administrator can download the image.” | CAPTURE-DETAIL, CAPTURE-DOWNLOAD | Correct metadata and PNG | Ownership |
| 23 | “Protected images and other students' metadata are denied.” | CAPTURE-DENIED, CAPTURE-OTHER | 403 / 404 | Failure handling |
| 24 | “Camera failure is logged without cancelling login.” | CAPTURE-FAILURE, SESSION-ACTIVE | Failed record; session still Active | Normal logout |
| 25 | “Normal workstation logout completes the session.” | SESSION-LOGOUT, SESSION-REPEAT, SESSION-AFTER | Completed, timestamp, repeat safe | Refresh availability |
| 26 | “The PC becomes available when online and unoccupied.” | Fresh HEARTBEAT without session_id, DASHBOARD | available true if Active/Working lab/PC | Reports |
| 27 | “The backend retains monitoring, failure and usage records.” | AGENT-ERROR, SYSTEM-LOGS, CAPTURE-SUMMARY, SESSION-SUMMARY | Persisted logs and grouped totals | State limitations |
| 28 | “This proves backend integration; physical device tests are next.” | Explain optional RFID flow and C#/hardware dependencies | Accurate scope, no claim of physical validation | Questions |

For a shorter demo, pre-record the actual timing on screen and explain the waiting period while demonstrating reports; do not pretend an immediate Offline response proves a timeout. Do not modify database timestamps during a live stale-heartbeat demonstration.

## 12. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Connection refused / ECONNREFUSED | Flask stopped or wrong port/origin | Check running terminal and base_url; use printed URL |
| Database OperationalError on startup/check | DB stopped, wrong host/port/password/name | Start correct MariaDB instance; verify private DB variables; do not display its password |
| `/` gives 404 or GET `/login` gives 405 | No root route / login requires POST | Use the documented method/path; no `/api` prefix |
| 400 JSON validation | Empty variables, quoted numeric IDs, missing fields, invalid enum | Inspect resolved request; all numeric IDs must be actual positive integers |
| 400 timestamp | Old/future clock, no timezone, capture before login | Use current UTC after login; synchronize clocks; check actual policy |
| 401 login | Wrong username/password or Disabled account | Verify account, reactivate appropriately; no assumed demo credentials |
| 401 protected route | Missing/expired/revoked JWT, disabled account, wrong key | Use correct token variable/header, obtain a fresh login; do not confuse agent/key/JWT |
| 403 | Correct authentication but wrong role/ownership, retired PC, wrong student session token | Match the endpoint permission table; never change roles merely to bypass a negative test |
| 404 | Wrong ID type, nonexistent record, hidden metadata or missing file | Distinguish user_id/student_id/session_id/capture_id; inspect prior response |
| 409 inventory/session | Duplicate identifiers, occupied PC/student, conflicting Active device | Reuse records; close only approved demo sessions; read current assignments |
| 409 heartbeat | Old/conflicting same-second sample, incomplete devices, completed/wrong session | Wait one second; fresh observed_at; re-fetch config; omit completed session_id |
| 409 capture | Wrong PC/session/camera, inactive session, disconnected camera or different existing image | Send fresh Connected heartbeat, keep correct Active session, use identical retry |
| 411 upload | Client sent no Content-Length | Use a real local file multipart upload; do not use streaming/chunked mode |
| 413 upload | Image/request/pixel limits exceeded | Use included small valid PNG; do not increase limits for the demonstration |
| 415 upload/JSON | Wrong format or Content-Type | Use RGB/RGBA non-interlaced PNG; let client set multipart; JSON writes use application/json |
| 500 / 503 | Storage/DB failure or missing configuration | Read server logs privately; verify writable private storage and DB; restart after config edits |
| Agent 503 even with raw key | Empty/invalid hash mapping or duplicate digests | Correct JSON mapping and unique SHA-256 digests; restart all workers |
| Dashboard still online after wait | Another agent/request is refreshing it; wrong PC selected | Stop all reporters for this demo PC and check last_heartbeat_at |
| Dashboard offline while session Active | Intentional separation of occupancy/connectivity | Show both fields; do not call it session completion |
| Available false after logout | Stale heartbeat, maintenance/defective PC or inactive lab | Fresh sessionless heartbeat and inspect status/condition/lab |
| Tokens stop working after restart | Secrets changed or account disabled; token expiry | Re-login with correct role; keep stable JWT secret for demo |
| Repeated `/logout` 401 | JWT revoked on first logout | Expected. Demonstrate idempotency with session-specific logout using Admin |
| Thunder import/script unavailable | Edition support or Postman-script incompatibility | Follow manual nine-step requests and copy variables yourself |

Current JWT revocation uses a process-local in-memory blocklist. A restart/multiple independent workers do not provide durable shared revocation. Demonstrate logout in one local process and disclose this limitation; do not claim durable production revocation.

## 13. Pre-demo checklist and reset

- [ ] Demo database is selected; existing records backed up where appropriate.
- [ ] V04 tables and correct Admin/Instructor/Student role rows are present.
- [ ] Virtual environment imports succeed; Flask is running at the recorded base_url.
- [ ] App database connectivity check succeeds.
- [ ] Actual test accounts exist; private credentials are known; tokens are fresh.
- [ ] Main and second Student accounts are Active; main student/PC have no leftover Active session.
- [ ] Existing inventory was reviewed; no duplicate 37-PC inventory was created.
- [ ] Chosen workstation is Active/Working in an Active laboratory.
- [ ] Assigned hardware IDs are correct; registration pair is not assigned to a student PC.
- [ ] Agent hash mapping and timing loaded successfully; AGENT-CONFIG succeeds.
- [ ] Workstation login key and agent key are separate and correctly selected per request.
- [ ] All API client variables resolve; numeric IDs are not quoted in JSON.
- [ ] Valid and invalid sample files are selected in their upload requests.
- [ ] Fresh timestamp generation is working; camera is simulated Connected before capture.
- [ ] Heartbeat senders can be stopped for the stale wait.
- [ ] Requests are saved and the full sequence has been rehearsed in the chosen client.
- [ ] Optional disabled/deleted accounts are reactivated if needed; tests are not mixed into the core demo by accident.
- [ ] No screenshots, shared exports or Git changes expose passwords, JWTs, raw agent keys or private `.env`.
- [ ] Expected statuses and actual outcomes are recorded; skipped hardware tests are marked Not Tested.

Before another rehearsal, complete/terminate only your own approved demo sessions, reactivate secondary demo accounts, reuse recorded inventory/account IDs, re-login for fresh JWTs, refresh device configuration and choose a new session for a new snapshot. Do not delete historical rows/files just to reset counters. For a clean deployment-sized dataset, use a fresh approved demo DB rather than altering real data. There is no general reset API.

## 14. Limitations and not-implemented interfaces

- **Not Implemented:** agent login endpoint, `/health`, `/me`, role-list API, token-refresh API, generic report export endpoints, registration-station entity/agent API, public image URLs, JPEG upload support, automatic completion solely from offline detection.
- Existing first-admin script is unsuitable as an interactive setup tool; use the explicit trusted local setup procedure above.
- Empty configuration is not a broken route: configure agent mappings/timing before claiming an authentication failure test succeeded.
- Hardware records/Connected values entered via Postman are simulated declarations. Only C# and physical testing can prove device measurements, actual webcam capture and reader/Arduino communication.
- Agent contract/timing/image permissions need client-team agreement. Snapshot files and SQL require coordinated backups; sudden process/power-loss reconciliation is not a live-demo claim.
- Earlier automated backend tests and this request replay are distinct from testing a Postman/Thunder GUI, deployed HTTPS, sustained 37-agent traffic, or final SPDP UAT.
- `tests/` and the schema files remain ignored by the existing Git configuration. The new `docs/` guide/collection/fixtures are shareable; fill secrets locally only. A teammate still needs the authoritative schema and approved configuration.
