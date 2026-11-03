from flask import Blueprint

from backend.controllers import reports_controller, audit_controller
from backend.utils.jwt import role_required, token_required


reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/reports/activities")
@token_required
@role_required("Admin", "Instructor")
def activities_report():
    return reports_controller.activities_report_control()


@reports_bp.get("/reports/submissions")
@token_required
@role_required("Admin", "Instructor")
def submissions_report():
    return reports_controller.submissions_report_control()


@reports_bp.get("/reports/student-progress")
@token_required
@role_required("Admin", "Instructor", "Student")
def student_progress_report():
    return reports_controller.student_progress_report_control()


@reports_bp.get("/audit-logs")
@token_required
@role_required("Admin")
def audit_logs():
    return audit_controller.list_audit_events_control()
