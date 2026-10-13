# Workstation and RFID API

The desktop application calls one of these endpoints for a **student workstation login**. The dashboard `POST /login` only authenticates a user; it does not start a laboratory session.

## Configuration

Set `JWT_SECRET_KEY` to a random secret of at least 32 characters and `WORKSTATION_API_KEY` to a separate random secret of at least 32 characters in `backend/.env`. Configure the desktop client with the workstation key and send it in `X-Workstation-Key` over HTTPS. The backend returns `503` for workstation login if the key is missing or too short. `tblRoles` must contain `Admin`, `Student`, and `Instructor` rows. Workstations and RFID readers must be provisioned in V04 tables before login; an RFID reader must be `Active`, `Connected`, and linked to the workstation.

## Login

| Method and path | JSON body | Result |
|---|---|---|
| `POST /workstation/login/manual` | `{"username":"student username or email","password":"...","workstation_id":1}` | `201` with `data.access_token`, `data.user`, and `data.session` |
| `POST /workstation/login/rfid` | `{"card_uid":"scanned UID","workstation_id":1,"reader_id":1}` | Same response; session records `RFID` and the card ID |

Both calls require `X-Workstation-Key`. The RFID endpoint checks the card, its sole active assignment, the student's active account, the configured reader, and the workstation. The manual endpoint checks the student's password and active account. Both reject an occupied workstation or a student already in an active session with `409`. The client should retain `session_id` and the student JWT returned by login.

Administrators manage cards through `GET/POST /rfid/cards`, `POST /rfid/cards/<card_id>/assignments`, `POST /rfid/cards/replacement`, `PATCH /rfid/cards/<card_id>/status`, and `GET /rfid/cards/<card_id>/assignments`. Deactivating or marking a card lost ends its active assignment. Reactivated cards must be assigned again. Replacement can accept a lost card from the student's assignment history and preserves its `Lost` status.

## Session completion and recovery

Send `Authorization: Bearer <student JWT>` with `POST /logout` on a normal workstation sign-out. A workstation token carries its session ID, so this call completes the session and revokes the token; a dashboard token has no session ID. The client may also call `POST /laboratory-sessions/<session_id>/logout` to complete a session without revoking the token. The owning student or an administrator can complete the session. Repeating the session-specific request returns the already completed status. A student cannot close another student's session.

The workstation JWT expires after `JWT_ACCESS_TOKEN_EXPIRES` seconds. The desktop client should sign out while it is valid. There is no token refresh endpoint yet; an administrator can terminate a session left active after the token expires.

While a workstation session is active, the desktop client should periodically call `POST /laboratory-sessions/<session_id>/heartbeat` with the workstation JWT. The backend writes an `Online` row in `tblPCStatus`. A dashboard token or another student's token cannot update that session.

An administrator can call `GET /laboratory-sessions/active`, `GET /laboratory-sessions/recovery-candidates?minutes=60`, and `PATCH /laboratory-sessions/<session_id>/terminate`. A candidate has a recent `Offline` PC status or no heartbeat (or PC status) within the requested interval; where no status has ever arrived, the login time is used. Candidates are only **signals for review**. The backend does not automatically close a session after a brief disconnection. Administrators can review `GET /laboratory-sessions/summary`; students can review their own `GET /laboratory-sessions` history.

The RFID reader, Arduino, and desktop transport have not been validated by the backend tests. A shared workstation key authenticates the desktop application fleet, not an individual reader or PC. V04 has no reader credential, device certificate, session heartbeat column, or durable JWT revocation table; per-device credentials and durable revocation require an agreed client protocol and schema extension. Heartbeats use the existing `tblPCStatus` history table.
