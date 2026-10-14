# Workstation monitoring API

## Contract status and scope

This is a **new backend contract proposed for C# integration**, implemented against `Database_Design_V04.sql`. No agent API or monitoring timing configuration previously existed. The existing [student workstation login API](WORKSTATION_API.md) is preserved. Backend tests use Flask and disposable MariaDB databases; C# and physical devices have not been tested.

SPDP reference: `C:/Users/ricken/Downloads/BSIT-3-1-SPDP.pdf`, pages 5–11. Register all 37 actual laboratory PCs, with reader/Arduino/camera sets on only five selected PCs. Register the sixth reader and Arduino as registration-station devices. These counts describe deployment scope, not seeded records or hardcoded dashboard totals. The backend receives login snapshots; it does not operate cameras or continuously record video.

## Deployment and credentials

Follow the normal [server setup](../README.md). Add the following to private `backend/.env`, then restart every backend worker:

```dotenv
MONITORING_HEARTBEAT_INTERVAL_SECONDS=30
MONITORING_OFFLINE_AFTER_SECONDS=120
MONITORING_MAX_CLOCK_SKEW_SECONDS=5
WORKSTATION_AGENT_KEY_HASHES={"1":"<64-character lowercase SHA-256 digest>"}
REGISTRATION_DEVICE_IDS={"rfid-readers":6,"arduinos":6}
```

Use actual database IDs. The **proposed** reporting interval is 30 seconds; a sample becomes stale at age **120 seconds or more**. Future clock differences up to 5 seconds are accepted. These are configurable choices awaiting desktop-team agreement, not SPDP timing requirements. Require `1 <= interval < timeout <= 86400` and `0 <= skew < timeout`. Missing/invalid timing returns `503` for timing-dependent operations.

Generate a unique high-entropy secret per PC, for example using Python `secrets.token_urlsafe(32)`. Deliver the raw secret securely to that PC; store only `hashlib.sha256(secret.encode()).hexdigest()` in the mapping. Tokens must contain 32–256 characters. Duplicate digests or malformed configuration return `503`. Remove/replace an entry and restart all workers to revoke/rotate it. Do not put secrets in source control, URLs or logs. No agent JWT endpoint or credential table is introduced.

Every agent call uses `Authorization: Bearer <this PC's raw agent secret>`. The URL workstation ID must match its configured key. Human JWTs, missing credentials and another PC's key return `401`. Retired PCs return `403`; a configured ID missing from the database returns `404`. Maintenance PCs may report diagnostics.

Human endpoints use existing user JWTs, with account-status and role checks. The fleet-wide `X-Workstation-Key` remains part of student workstation login; it is not an agent credential. Agents cannot manage accounts, authenticate students or close sessions through these new endpoints.

Use HTTPS for deployed agents, consistent configuration across backend workers, and private access controls for agent secrets. Configure production proxy rate limits, request limits and connection timeouts. The repository's localhost Flask server is for development, with no production TLS configuration.

## Responses and validation

URLs have no `/api` prefix. JSON requires `Content-Type: application/json` and a maximum 64 KiB body. Unsupported fields, repeated query parameters, invalid types and unknown enum values are rejected.

```json
{"success":true,"message":"Heartbeat accepted.","data":{"pc_status_id":123,"duplicate":false}}
```

```json
{"success":false,"message":"Invalid workstation agent credentials.","error":null}
```

| Status | Meaning / client action |
|---|---|
| 200 | Successful read/update or identical heartbeat/snapshot retry |
| 201 | Record created; `/errors` also uses 201 for deduplicated reports |
| 400 | Invalid fields, JSON or timestamp; correct the request |
| 401 / 403 | Invalid credentials / forbidden operation |
| 404 | Record/file missing; unauthorized capture metadata also uses 404 |
| 409 | Identifier/assignment/session conflict, old sample or concurrent conflict; reload before retrying |
| 411 / 413 / 415 | Missing upload length / oversized body or image / unsupported media |
| 500 / 503 | Internal failure / unavailable storage or configuration; bounded retry with backoff |

Flask-generated unknown-route/method errors are outside this JSON contract. Collect fresh metrics after a stale-sample error rather than retrying old data. Synchronize PC/server clocks. Timestamps require ISO-8601 with `Z` or an explicit offset and are normalized to whole seconds. New responses use UTC `Z`. PC samples preserve the existing database-local timestamp convention used by session heartbeats/recovery and views; they are converted to/from UTC at the repository boundary. New capture/log timestamps are UTC. Keep the database timezone fixed (for example, the existing Asia/Manila offset); V04 DATETIME columns do not preserve historic timezone/DST changes.

## Agent endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/agent/workstations/{id}/configuration` | Discover active assigned devices, timing and snapshot limits |
| POST | `/agent/workstations/{id}/heartbeats` | Atomic metrics, device availability and heartbeat submission |
| POST | `/agent/workstations/{id}/captures` | One login snapshot per session/camera |
| POST | `/agent/workstations/{id}/capture-failures` | Failed capture record without a file |
| POST | `/agent/workstations/{id}/errors` | Agent/device error report |

### Configuration

`GET /agent/workstations/1/configuration` returns this `data`:

```json
{
  "workstation_id": 1,
  "pc_name": "PC-1",
  "laboratory_id": 1,
  "devices": [{"kind":"rfid-readers","id":1,"connection_status":"Connected"}],
  "heartbeat_interval_seconds": 30,
  "offline_after_seconds": 120,
  "max_clock_skew_seconds": 5,
  "snapshot_max_bytes": 5242880,
  "snapshot_max_pixels": 16777216,
  "snapshot_format": "PNG (8-bit RGB/RGBA, non-interlaced)"
}
```

Kinds are `rfid-readers`, `arduinos`, `cameras`. An unequipped PC receives `devices: []`. These are registered IDs and last reported connection states; the desktop measures actual availability. Re-fetch after assignment conflicts. Administrators provision serial-port settings from hardware inventory.

### Heartbeats

`POST /agent/workstations/1/heartbeats`:

```json
{
  "observed_at": "2026-10-14T03:00:00Z",
  "cpu_usage": 21.5,
  "ram_usage": 46.2,
  "storage_usage": 62.1,
  "network_status": "Connected",
  "online_status": "Online",
  "session_id": 42,
  "devices": [
    {"kind":"rfid-readers","id":1,"connection_status":"Connected"},
    {"kind":"arduinos","id":1,"connection_status":"Connected"},
    {"kind":"cameras","id":1,"connection_status":"Disconnected"}
  ]
}
```

Use a current timestamp, not the literal example. Required: `observed_at`, all three numeric metrics, `network_status`, `devices`. Metrics are finite percentages from 0 to 100, stored to two decimals. Strings/booleans are rejected. Proposed storage metric: percent used on the monitored system volume; agree the volume and sampling method with the desktop team. V04 cannot store per-volume/byte telemetry.

`online_status` defaults to `Online`; `Offline` supports best-effort orderly shutdown reporting. `session_id` is optional/null; if supplied it must be active on this PC. Dashboard occupancy always comes from actual session records, even when omitted by the agent.

Network/device connection states are `Connected` or `Disconnected`. Report **exactly every active assigned device**, including disconnected devices, with unique kind/ID pairs (maximum 20). Unequipped PCs send an empty list; camera/RFID sample status becomes `Not Available`. Arduino availability updates its inventory row and logs changes, since `tblPCStatus` has no Arduino field.

The transaction locks the PC, validates associations, inserts the sample, updates device states and logs changes together. Older samples or same-second conflicting metrics return `409`; identical stored samples return `200` without inserting again. Send at most one new sample per second. Same-second retries never change device state; report subsequent device changes using a newer sample. Unrelated PCs can report concurrently.

Dashboard connectivity is evaluated on read: missing/stale samples count offline without closing sessions or rewriting history. Reconnection appears after a fresh accepted sample. A PC is available only when online, unoccupied, Active/Working, and in an Active laboratory. Offline PCs with hardware are marked hardware-unavailable even if their last stored device state says Connected.

Legacy student-session heartbeats leave `network_status` NULL. New monitoring queries require non-NULL network status so student JWT heartbeats cannot establish agent connectivity. Do not insert other telemetry directly under this convention. Existing SQL views remain raw historical summaries; they do not implement freshness or agent authentication.

### Login snapshots

After successful student workstation login, retain its session ID. Discover the assigned camera, report current availability, capture on the desktop and upload promptly while the session is active. If capture fails, report the failure without cancelling a valid login.

`POST /agent/workstations/1/captures` uses `multipart/form-data`, a **Content-Length** header, and exactly:

| Field | Value |
|---|---|
| `session_id` | Positive integer as form text |
| `camera_id` | Positive integer as form text |
| `captured_at` | ISO-8601 timestamp with timezone |
| `image` | One PNG file |

The proposed image contract is static, non-interlaced, 8-bit RGB/RGBA PNG. C# must encode to this format. JPEG, indexed/grayscale PNG, animations, invalid CRC/compression, truncated images, excessive pixels and trailing bytes are rejected. Bounded decompression validates scanline lengths/filter values; ancillary metadata is stripped. Format reference: [W3C PNG specification](https://www.w3.org/TR/png-3/).

Defaults: 5 MiB image data, 16,777,216 pixels, plus up to 64 KiB multipart overhead. Caller filenames/extensions are not trusted. Files receive UUID names in private `instance/camera_captures`. Optionally set absolute `SNAPSHOT_STORAGE_ROOT` in `.env`; Flask app configuration can override size/pixel limits. Do not expose storage through a public server directory. Back up files and SQL together and share storage across backend workers.

The active session and Active/Connected camera must belong to the authenticated PC. The timestamp cannot precede login or exceed the configured reporting window. Student identity comes from the session, never a caller-supplied student ID.

Success: `201`, `data = {"capture_id":1,"capture_status":"Captured","duplicate":false}`. One successful image per session/camera is accepted. An identical canonical file retry returns the original ID with `200`; different content returns `409`. Retries after session completion are rejected. Do not queue old login snapshots across long outages.

Files are flushed before metadata commits. Confirmed rollbacks remove uncommitted files; uncertain commit outcomes preserve files until SQL can be checked. SQL and files are not one atomic transaction: process/power failure can leave orphaned files. Reconcile successful metadata filenames against private storage after outages; retain uncertain files while the database is unavailable.

### Capture failures

`POST /agent/workstations/1/capture-failures`:

```json
{"session_id":42,"camera_id":1,"captured_at":"2026-10-14T03:00:00Z","reason":"Disconnected"}
```

Reasons: `Disconnected`, `Unavailable`, `Capture error`, `Upload error`. The same PC/session/camera association is validated. The backend writes `Failed`, an empty path (V04 requires non-NULL), and a warning log; no file is created and the session stays active. Repeated failures per session/camera return the original failure with `200`; later success remains possible. A disconnection cannot overwrite a newer heartbeat's device state. A PC with no registered camera cannot create a capture row; use a general Camera error when appropriate.

### Error reports

`POST /agent/workstations/1/errors`:

```json
{"level":"Error","component":"Arduino","message":"Serial port unavailable"}
```

Levels: `Info`, `Warning`, `Error`, `Critical`. Components: `Agent`, `Network`, `Camera`, `RFID`, `Arduino`. Message: 1–2000 UTF-8 bytes without credentials, student data or images. Server-generated UTC time is used. Identical PC/component/level/message reports within 60 seconds reuse the log ID. Response `201`: `data = {"system_log_id":1,"duplicate":false}` (or `true`).

## Inventory, dashboard and reports

| Method and URL | Access | Result |
|---|---|---|
| GET `/laboratories`, `/laboratories/{id}` | Admin, Instructor | Laboratory records |
| POST `/laboratories`; PATCH `/laboratories/{id}` | Admin | Register/update, including activation |
| GET `/workstations`, `/workstations/{id}` | Admin, Instructor | PC inventory; list filter `laboratory_id` |
| POST `/workstations`; PATCH `/workstations/{id}` | Admin | Register/update/laboratory assignment |
| GET `/hardware/{kind}`, `/hardware/{kind}/{id}` | Admin, Instructor | Device/assignment report; list filter `workstation_id` |
| POST `/hardware/{kind}`; PATCH `/hardware/{kind}/{id}` | Admin | Register/update/assign hardware |
| GET `/monitoring/dashboard?laboratory_id=1` | Admin, Instructor | All PCs, connectivity, occupancy, hardware counts, metrics |
| GET `/monitoring/workstations/{id}/history` | Admin, Instructor | Agent samples, newest first |
| GET `/monitoring/logs?workstation_id=1` | Admin | Inventory changes, device transitions, errors |
| GET `/camera-captures?session_id=42`, `/camera-captures/{id}` | Admin; Student own records | Metadata without storage paths |
| GET `/camera-captures/{id}/file` | Admin | Private PNG download, no public URL |
| GET `/camera-captures/summary` | Admin | Counts by PC, camera, Captured/Failed |

Lists accept `limit` (1–1000, default 100) and `offset` (default 0), returning an array in `data`. Detail/write `data` is a record. Dashboard/capture summary are unpaginated. Reports reuse these endpoints. Inventory deletion is represented by inactive/maintenance/retired states to preserve history; no DELETE endpoint is added.

| Resource | Required on create | Other writable fields |
|---|---|---|
| laboratories | `laboratory_name`, `room_number` | `description`, `status` |
| workstations | `laboratory_id`, `pc_name`, `asset_tag` | `ip_address`, `processor`, `ram`, `storage`, `operating_system`, `status`, `condition` |
| rfid-readers | `device_name` | `workstation_id`, `serial_number`, `connection_status`, `status` |
| arduinos | `device_name` | `workstation_id`, `serial_port`, `connection_status`, `status` |
| cameras | `device_name`, `workstation_id` | `connection_status`, `status` |

Laboratory status: `Active`/`Inactive`. PC status: `Active`/`Under Maintenance`/`Retired`; condition: `Working`/`Defective`/`For Inspection`. Device status: `Active`/`Inactive`/`Defective`; connection: `Connected`/`Disconnected`. Lengths follow V04 with a 4000-character API limit for laboratory description. Optional nullable text can be cleared with null. PATCH takes a nonempty subset.

Unique PC name/asset tag and reader serial conflicts return `409`. Transaction checks permit one Active device per kind per PC. Moves reset device connection to Disconnected. Moving hardware/PCs or changing PC maintenance status while occupied is rejected; laboratory deactivation also requires no active sessions. Conflicting legacy/direct-SQL assignments require administrator cleanup.

Readers/Arduino may have null workstation IDs. `REGISTRATION_DEVICE_IDS` designates the actual registration pair; API reassignment is blocked while designated. Other null devices are `Unassigned`. V04 has no registration-station entity/agent identity or pair foreign key. No fake 38th PC is created. Admin can maintain registration hardware records; autonomous registration-station telemetry needs a separately agreed interface/schema extension. Cameras require a PC in V04.

Dashboard `data`: `counts`, `workstations`, `as_of`, `heartbeat_interval_seconds`, `offline_after_seconds`. Counts: `total`, `online`, `offline`, `in_use`, `available`, `with_rfid`, `with_camera`, `with_arduino`, `hardware_unavailable`. Capabilities count Active devices. Each PC appears once even with historical hardware/multiple sessions. Admin additionally receives `current_student` when exactly one active session exists; Instructor receives no student identity. Image downloads are conservatively Admin-only pending agreement on SPDP's authorized-personnel policy.

## Integration dependencies

- Agree timing, storage sampling, PNG encoding, image permissions and secure credential provisioning with C# developers.
- Register real inventory; provision all PCs. No production records are seeded by this work.
- Test C# manual/RFID login → session → heartbeat → snapshot/failure → logout with physical devices.
- Test network interruption, clock skew, backend restart and camera reconnection. Offline detection must leave sessions available for existing recovery review.
- Plan telemetry/log retention and load testing. Evaluate an explicit migration for `tblPCStatus(workstation_id, recorded_at, id)` before sustained deployment; no schema/index was changed here.
- V04 lacks telemetry source/received-at columns, Arduino sample data, camera/Arduino serial identifiers and dedicated assignment history. Current conventions use network-status presence and system logs. Make these explicit in a future schema migration before accepting other telemetry writers.
