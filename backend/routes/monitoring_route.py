from flask import Blueprint

from backend.controllers import monitoring_controller as controller
from backend.utils.agent_auth import agent_required
from backend.utils.jwt import role_required, token_required


monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.route("/laboratories", defaults={"kind": "laboratories"}, methods=["GET", "POST"])
@monitoring_bp.route("/workstations", defaults={"kind": "workstations"}, methods=["GET", "POST"])
@monitoring_bp.route("/hardware/<any('rfid-readers','arduinos','cameras'):kind>", methods=["GET", "POST"])
@token_required
@role_required("Admin", "Instructor")
def inventory_list(kind):
    return controller.inventory_list_control(kind)


@monitoring_bp.route("/laboratories/<int:record_id>", defaults={"kind": "laboratories"}, methods=["GET", "PATCH"])
@monitoring_bp.route("/workstations/<int:record_id>", defaults={"kind": "workstations"}, methods=["GET", "PATCH"])
@monitoring_bp.route(
    "/hardware/<any('rfid-readers','arduinos','cameras'):kind>/<int:record_id>",
    methods=["GET", "PATCH"],
)
@token_required
@role_required("Admin", "Instructor")
def inventory_detail(kind, record_id):
    return controller.inventory_detail_control(kind, record_id)


@monitoring_bp.get("/monitoring/dashboard")
@token_required
@role_required("Admin", "Instructor")
def dashboard():
    return controller.dashboard_control()


@monitoring_bp.get("/monitoring/workstations/<int:workstation_id>/history")
@token_required
@role_required("Admin", "Instructor")
def history(workstation_id):
    return controller.history_control(workstation_id)


@monitoring_bp.get("/monitoring/logs")
@token_required
@role_required("Admin")
def logs():
    return controller.logs_control()


@monitoring_bp.get("/agent/workstations/<int:workstation_id>/configuration")
@agent_required
def agent_configuration(workstation_id):
    return controller.agent_configuration_control(workstation_id)


@monitoring_bp.post("/agent/workstations/<int:workstation_id>/heartbeats")
@agent_required
def heartbeat(workstation_id):
    return controller.heartbeat_control(workstation_id)


@monitoring_bp.post("/agent/workstations/<int:workstation_id>/errors")
@agent_required
def agent_error(workstation_id):
    return controller.agent_error_control(workstation_id)


@monitoring_bp.post("/agent/workstations/<int:workstation_id>/captures")
@agent_required
def capture_upload(workstation_id):
    return controller.capture_upload_control(workstation_id)


@monitoring_bp.post("/agent/workstations/<int:workstation_id>/capture-failures")
@agent_required
def capture_failure(workstation_id):
    return controller.capture_failure_control(workstation_id)


@monitoring_bp.get("/camera-captures")
@token_required
@role_required("Admin", "Student")
def capture_list():
    return controller.capture_list_control()


@monitoring_bp.get("/camera-captures/summary")
@token_required
@role_required("Admin")
def capture_summary():
    return controller.capture_summary_control()


@monitoring_bp.get("/camera-captures/<int:capture_id>")
@token_required
@role_required("Admin", "Student")
def capture_detail(capture_id):
    return controller.capture_detail_control(capture_id)


@monitoring_bp.get("/camera-captures/<int:capture_id>/file")
@token_required
@role_required("Admin")
def capture_download(capture_id):
    return controller.capture_download_control(capture_id)
