import hashlib
import hmac
import json
import os
import re
from functools import wraps

from flask import current_app, request

from backend.utils.api_response import error
from backend.utils.domain_error import DomainError


def configure_monitoring(app):
    for name in ("WORKSTATION_AGENT_KEY_HASHES", "REGISTRATION_DEVICE_IDS"):
        try:
            app.config[name] = json.loads(os.getenv(name, "{}"))
        except ValueError:
            app.config[name] = None

    for name in (
        "MONITORING_HEARTBEAT_INTERVAL_SECONDS",
        "MONITORING_OFFLINE_AFTER_SECONDS",
        "MONITORING_MAX_CLOCK_SKEW_SECONDS",
    ):
        try:
            app.config[name] = int(os.getenv(name, ""))
        except ValueError:
            app.config[name] = None

    app.config["SNAPSHOT_MAX_BYTES"] = 5 * 1024 * 1024
    app.config["SNAPSHOT_MAX_PIXELS"] = 4096 * 4096
    if os.getenv("SNAPSHOT_STORAGE_ROOT"):
        app.config["SNAPSHOT_STORAGE_ROOT"] = os.environ["SNAPSHOT_STORAGE_ROOT"]


def heartbeat_policy():
    interval = current_app.config.get("MONITORING_HEARTBEAT_INTERVAL_SECONDS")
    timeout = current_app.config.get("MONITORING_OFFLINE_AFTER_SECONDS")
    skew = current_app.config.get("MONITORING_MAX_CLOCK_SKEW_SECONDS")
    if (
        type(interval) is not int or type(timeout) is not int
        or type(skew) is not int or not 1 <= interval < timeout <= 86400
        or not 0 <= skew < timeout
    ):
        raise DomainError("Monitoring heartbeat policy is not configured.", 503)
    return interval, timeout, skew


def agent_required(function):
    @wraps(function)
    def decorated(workstation_id, *args, **kwargs):
        hashes = current_app.config.get("WORKSTATION_AGENT_KEY_HASHES")
        if (
            not isinstance(hashes, dict) or not hashes
            or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
                   for v in hashes.values())
            or len(set(hashes.values())) != len(hashes)
        ):
            return error("Agent authentication is not configured.", 503)

        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        expected = hashes.get(str(workstation_id))
        if (
            not expected or not 32 <= len(token) <= 256
            or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), expected)
        ):
            return error("Invalid workstation agent credentials.", 401)
        return function(workstation_id, *args, **kwargs)

    return decorated
