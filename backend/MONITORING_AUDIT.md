# Laboratories, hardware and monitoring audit

Date: 2026-10-14. Scope: backend inventory, agent authentication, monitoring, snapshots and reports. This report distinguishes verified backend behavior from deployment and physical integration still required.

## Sources and existing implementation

- Authoritative schema: `database/Database_Design_V04.sql`; all eight owned tables, their columns/enums/constraints and referenced session/student/user tables were inspected.
- Existing reporting: `database/views.sql`, including inventory, session/capture, latest-PC, dashboard and laboratory-summary views. All 28 views were loaded against V04 during testing.
- SPDP: `C:/Users/ricken/Downloads/BSIT-3-1-SPDP.pdf`, pages 5–11 for scope/hardware, metrics and login snapshots; page 15 for integration/UAT expectations. The plan specifies 37 PCs, five equipped workstation sets and a separate registration reader/Arduino pair. It does not define an agent REST contract or heartbeat timing.
- Existing code reviewed: `__init__.py`, `database/connection.py`, `config/settings.py`, `utils/jwt.py`, `utils/api_response.py`, `utils/domain_error.py`, account/auth/RFID/session services, repositories, controllers and routes, `WORKSTATION_API.md`, and the existing account/RFID/session tests.

Before this task, the backend already provided student workstation login, session creation/logout/recovery, shared human JWT/role checks and a student session heartbeat. Inventory/reporting tables and views existed. There were **no registered laboratory/workstation/hardware management routes, independent workstation-agent credentials, metrics ingestion endpoints, freshness-aware dashboard API, or camera upload/retrieval/failure endpoints**. A table/view alone did not implement these requirements.

## A. Implementation status matrix

“Verified” below means implemented and exercised with Flask requests against disposable MariaDB databases, within the documented backend contract. It does not mean C# or physical hardware integration is complete.

| Requirement | Before → current status | Implementation | Required action |
|---|---|---|---|
| Laboratory management | Missing → Verified | `inventory_service.save_inventory_service`, inventory routes | Register actual laboratory |
| Workstation management | Missing → Verified | Same service, `inventory_repository` | Register all 37 real PCs |
| Hardware registration | Missing → Verified | Inventory routes/service, V04 device tables | Register six readers, six Arduino and five cameras |
| Hardware assignment | Missing → Verified | `save_inventory_service`, `check_device_assignment_repo` | Configure actual five sets and registration pair |
| Agent authentication | Missing → Verified | `agent_auth.agent_required` | Secure per-PC secret provisioning and HTTPS |
| Heartbeat processing | Partial (student only) → Verified | `heartbeat_service`, `insert_heartbeat_repo` | Adopt proposed agent contract |
| Monitoring metrics | Missing → Verified | `metric`, `heartbeat_service` | Agree desktop sampling/volume definition |
| Stale heartbeat detection | Missing → Verified | `dashboard_service` | Agree configurable 30s/120s/5s policy |
| Dashboard summaries | Partial (raw views) → Verified | `dashboard_rows_repo`, `dashboard_service` | Connect dashboard UI |
| Snapshot uploads | Missing → Verified | `upload_capture_service`, `validate_png` | Verify actual C# PNG encoding |
| Snapshot retrieval | Missing → Verified | Metadata ownership checks, Admin file route | Confirm image access/retention policy |
| Capture failure logging | Missing → Verified | `capture_failure_service` | Connect desktop error path |
| Workstation/device reports | Partial (views) → Verified | Inventory, dashboard/history, capture summary | UI/export consumption as needed |
| System error logging | Partial (table) → Verified | `agent_error_service`, `system_log_repo`, controller fallback | Production log retention/rate limiting |

Registration-station **records** are implemented. Autonomous monitoring of that separate server station is **Partial**: V04 has no station/agent identity for it. No invented workstation row or relationship was added.

## B. Confirmed issues and corrections

| Severity | Location/function | Confirmed problem and cause | Correction / remaining action |
|---|---|---|---|
| High | Existing `repositories/laboratory_sessions_repository.py::heartbeat_session_repo`; app route registrations | Only student session heartbeats existed, without metrics or an independent PC identity. Reusing that token would not establish trusted machine telemetry. | Preserved existing endpoint; added workstation-scoped `agent_required` and separate monitoring endpoints. |
| High | Previously absent inventory API; `Database_Design_V04.sql` device tables | FKs validate references but do not prevent two Active devices of the same kind being assigned to one PC. | New transactional inventory service locks affected PCs and uses current locking reads for conflict/occupancy checks. Concurrent creates and reassignment tested. Direct SQL writers remain outside this guarantee. |
| High | Previously absent camera handling; `tblCameraCaptures` | No upload validation, authorization, safe storage or cross-table PC/session/camera consistency checks existed. Separate FKs cannot enforce those associations. | Added agent-scoped uploads, active session/camera checks, bounded PNG validation, private filenames/storage and protected retrieval. |
| Medium | `database/views.sql::vw_latest_pc_status`, `vw_workstation_dashboard`, `vw_laboratory_monitoring_summary` | Latest recorded Online state is historical and does not become Offline when the agent stops. Views already describe this limitation. | Preserve raw views; API derives connectivity from configurable freshness and session occupancy independently. |
| Medium | `tblRFIDReaders`, `tblArduinoDevices` nullable workstation FK | NULL alone cannot distinguish unassigned stock from registration hardware. No station entity exists. | Explicit `REGISTRATION_DEVICE_IDS` maps the registration pair without schema changes. Separate station telemetry remains a dependency. |
| Medium | `tblPCStatus`; legacy heartbeat/recovery consumers | No telemetry source or timezone column. Mixing new UTC samples with legacy database-local samples would misorder history and create false recovery candidates. | New repository converts PC times at the UTC/API boundary while preserving database-local storage; non-NULL network status identifies new agent samples. Explicit +08:00 test covers recovery, dashboard and captures. Future source/received-at columns recommended. |
| Medium | New `inventory_repository::require_idle_repo`, `check_device_assignment_repo` during implementation review | Repeatable-read transactions could use a snapshot established before acquiring the PC lock during PATCH reassignment. | Added `FOR UPDATE` current reads; synchronized concurrent reassignment test confirms one winner and one conflict. |
| Medium | New `captures_service::upload_capture_service` during implementation review | Deleting a file after every commit exception could remove an image whose SQL commit succeeded but acknowledgement was lost. | Check committed metadata on a fresh connection before deletion. Preserve uncertain files; simulated lost-acknowledgement test confirms file/metadata survive and retry succeeds. |
| Low | `backend/.env.example` | Bare variable names were not a usable populated configuration template. | Added valid KEY=value syntax and documented proposed monitoring settings, with empty secret fields. Real `.env` remains untouched. |

The newly added implementation issues above were found and corrected during this task; they were not defects in pre-existing camera/agent modules, which did not exist.

### Schema limitations and deployment concerns

- **No DDL or views changed.** All fields and enums come from V04. Values are parameterized; dynamic table/column identifiers come only from internal allowlists.
- Registration pair, device assignment history, Arduino telemetry history and agent credentials have no dedicated schema entities. Registration/credential configuration and `tblSystemLogs` cover the current contract. Arduino/camera physical serial uniqueness cannot be enforced without actual serial columns.
- `tblCameraCaptures.file_path` is required even for Failed captures: empty string means no file. Failed rows are never downloadable.
- File storage and SQL cannot form one transaction. Rollback, storage failure and uncertain acknowledgement are covered; abrupt machine/power failure still requires storage reconciliation and coordinated backups. No automatic destructive orphan cleanup was introduced.
- `tblPCStatus` has no source/received-at fields. The non-NULL network-status convention is valid for reviewed writers; external/direct SQL writers must coordinate. Propose explicit columns before broadening ingest sources.
- Keep the DB timezone fixed. V04 DATETIME lacks historical timezone information; migrating historic timestamps or supporting DST changes needs an explicit data plan.
- A composite PC-history index `(workstation_id, recorded_at, id)` and retention policies should be evaluated before sustained use. Thirty-second reports from 37 PCs produce roughly 106,560 rows/day. No load/endurance benchmark was run.
- Existing student login still uses a shared fleet key, and existing JWT revocation remains its previous design. The new agent key does not expand those privileges; redesigning student login/revocation is outside this task.
- Default file access is Admin-only; Students may view only their own capture metadata. Instructor inventory/dashboard access does not include student identity or images. These conservative permissions require team confirmation because the SPDP does not supply a complete image permission matrix.

## C. Implementation summary and architecture

Created:

| File | Main responsibilities |
|---|---|
| `routes/monitoring_route.py` | Inventory, dashboard/history/logs, agent configuration/heartbeat/error/capture routes, capture metadata/file/summary routes |
| `controllers/monitoring_controller.py` | Bounded request parsing, role-sensitive writes, response conversion, error mapping, private downloads |
| `repositories/inventory_repository.py` | Allowlisted CRUD, transaction/resource handling, PC locks, assignment checks, logs |
| `repositories/monitoring_repository.py` | Agent sample storage/history, one-row-per-PC dashboard, active student details, logs |
| `repositories/captures_repository.py` | Session/camera validation queries, capture persistence, ownership and summary queries |
| `services/inventory_service.py` | Field/enum/reference validation, registration designation, occupied-PC and device-assignment rules |
| `services/monitoring_service.py` | Agent configuration, metrics/time validation, ordered/idempotent heartbeat handling, derived dashboard, error deduplication |
| `services/captures_service.py` | Safe file storage, capture associations, timestamps, idempotency and failure handling |
| `utils/agent_auth.py` | Config loading, unique per-PC secret verification and heartbeat policy |
| `utils/snapshot_image.py` | Bounded RGB/RGBA PNG validation and metadata stripping using standard-library tools |
| `MONITORING_API.md`, `MONITORING_AUDIT.md` | Proposed integration contract and this review |
| `../tests/test_monitoring.py` | Disposable-database integration, concurrency and failure tests |

Modified `__init__.py` only to configure/register the monitoring module; `.env.example`, `../README.md` and `WORKSTATION_API.md` for accurate setup and contract links. Existing account, RFID, session and project application code is preserved. No new application dependency or architectural layer was introduced. Test/PDF tooling is not a backend dependency.

Verified paths:

1. Agent request → route → workstation-bound key decorator → controller → service → transactional repository → V04 tables → existing JSON envelope.
2. Admin/Instructor request → existing JWT/account-status/role decorators → controller → inventory/report service → repository → role-appropriate response.
3. C#-style multipart request → agent authentication → bounded PNG/association validation → private file → SQL metadata commit → capture ID. Admin file request → existing human authentication → metadata check → constrained path → private attachment response.

There is no backend webcam/serial/Arduino implementation. No new endpoint automatically ends sessions on missing heartbeats or capture errors.

## D. Testing and reproducibility

Environment: Windows, Python 3.12, Flask 3.0.3, MariaDB 10.4.32/InnoDB from XAMPP. A disposable instance on `127.0.0.1:3307` was initialized under ignored `tests/.monitoring_db`; application databases were not used. Each test creates and drops a separate `clms_audit_*` database from the exact V04 file.

Initial attempts failed before useful verification because port 3306 was unavailable and Windows sandbox permissions prevented access to `TemporaryDirectory` folders. Tests now use normal, isolated UUID directories with explicit cleanup. A timing-sensitive test was corrected to derive its old timestamp from the submitted sample instead of wall-clock elapsed time. These failed attempts were not counted as passing results.

**Final result: PASS — 36 tests in 93.809 seconds (25 monitoring tests + 11 existing account/RFID/session regression tests).** This includes explicit non-UTC database coverage. Python compilation and Git whitespace checks also passed. All backend test rows below passed; deployment/hardware rows are explicitly Not Tested.

Run against a local disposable/test server on port 3307 with the fixture's root/no-password credentials:

```powershell
python -c "import sys, unittest; sys.path.insert(0, 'tests'); import test_accounts_rfid_sessions as f; f.DB_BASE['port']=3307; suite=unittest.TestSuite([unittest.defaultTestLoader.discover('tests', pattern=name) for name in ['test_monitoring.py', 'test_accounts_rfid_sessions.py']]); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())"
```

Do not point these fixtures at a production server/account. The server must already be running and permit disposable database creation. Local raw output: `../tests/monitoring_test_results.txt`. `tests/` remains ignored per the user's existing preference, so the test suite/result file will not accompany an ordinary Git push. Schema/views are also currently ignored and must be shared separately for reproducibility.

| Test scenario | Expected behavior | Actual verification |
|---|---|---|
| Laboratory/PC create, update, list, duplicates and missing FK | Valid CRUD; reject duplicates/invalid reference; enforce roles | Assertions cover 201/200/409/404/403 |
| Device register/assign/move, registration pair, duplicate serial | Save valid device; reject conflicts; reset connection on move | Assertions cover values, statuses and registration designation |
| Concurrent device create and PATCH assignment | One winner; one 409; exactly one assignment | Real concurrent database transactions |
| Agent auth and configuration | Own PC succeeds; missing/human/wrong-PC credentials denied; retired denied | 200/201, 401, 403 and config values checked |
| Metrics and devices | Valid percentages persisted; device state updated; invalid fields rejected | DB values, rounding, 400/409 rejection and Arduino conflict checked |
| Concurrent/repeated/out-of-order heartbeats | One sample on retry; stale/conflicting values rejected | 201/200 pair, row count 1; 409 for older/conflicting sample |
| Missing heartbeat/reconnection/legacy heartbeat | Stale offline, fresh online; active session preserved | Derived counts/status and active session DB row checked |
| Dashboard scope/permissions | 37 PCs, five equipped; no join duplication; no Instructor student identity | Exact totals and response fields checked |
| Valid snapshot and concurrent retry | Private file + metadata; one row/file for identical retries | 201/200, content and row/file counts checked |
| Invalid image/size/CRC/dimensions/truncation and wrong associations | Reject without successful capture/file | 400/409/413/415 and DB/file absence checked |
| Metadata stripping and path manipulation | Remove ancillary content; reject unsafe stored path | Download bytes compared; traversal returns 404 |
| Snapshot authorization | Admin download; owner metadata only; other Student denied | 200/403/404 and private response headers checked |
| Camera failure | Failed row, no file, session remains Active | DB states and download 404 checked |
| DB insert failure, unavailable storage, heartbeat logging failure | Roll back changes; safe API error; clean uncommitted file | Fault injection, DB/file inspection, 500 response |
| Commit acknowledgement lost | Keep committed image; retry resolves existing capture | Fault injection verifies one file/row and retry 200 |
| Agent logs and permission checks | Deduplicate repeated errors; restrict log reading | DB count, source and role checks |
| Occupied-PC maintenance/assignment | Reject inventory changes that displace active session | 409 responses with session retained |
| V04 views | All views compile; dashboard does not multiply PCs | 28 created; exact dashboard cardinality |
| Non-UTC database | Fresh agent sample does not trigger session recovery; capture timing valid | Explicit +08:00 connection and database age/response assertions |
| Account/RFID/session regression | Preserve established authentication, assignment, concurrency and logout behavior | Existing 11-test suite executed |
| Real C# HTTP client, TLS proxy, 37 physical agents and RFID/Arduino/camera devices | Complete system integration | **Not Tested** |
| MySQL 8, long-term load/retention, process/power-loss recovery | Deployment-specific behavior | **Not Tested** |

`python -m compileall -q backend tests/test_monitoring.py` and `git diff --check` are also run. Expected fault-injection tests intentionally emit server error logs; those messages do not indicate unexpected test failures.

## E. Integration dependencies and final assessment

The [API contract](MONITORING_API.md) defines URLs, methods, headers, payloads, response structures, status codes, roles, timestamps and retry rules. It is available for C# integration. Production credentials/configuration, actual hardware inventory, TLS, storage/retention policy and client agreement remain deployment work.

| Major responsibility | Completion category |
|---|---|
| Backend laboratory/workstation CRUD and maintenance | Fully Implemented and Tested within documented contract |
| Backend hardware records/assignments | Fully Implemented and Tested within V04 limits |
| Registration-station autonomous agent telemetry | Partially Implemented: records only; identity/interface dependency |
| Workstation agent auth/configuration and ingest | Fully Implemented and Tested on backend |
| Metrics, connectivity, dashboard/history/reports/logs | Fully Implemented and Tested on backend; endurance Not Tested |
| Snapshot upload, metadata, download and failure handling | Fully Implemented and Tested on backend; abrupt power-loss behavior Not Tested |
| Actual C# workstation/hardware integration | Blocked by Dependencies: client implementation/configuration and physical testing |
| Production rollout and SPDP UAT | Partially Implemented: backend verification complete; deployment/UAT pending |

This is ready for coordinated backend/client integration testing after configuration. It is **not** a claim of complete production deployment, physical integration, or SPDP acceptance.
