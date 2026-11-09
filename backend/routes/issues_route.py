from flask import Blueprint, g

from backend.controllers import issues_controller
from backend.utils.jwt import role_required, token_required


issues_bp = Blueprint("pc_issues", __name__)


@issues_bp.post("/workstations/<int:workstation_id>/issues")
@token_required
@role_required("Admin", "Instructor", "Student")
def report_issue(workstation_id):
    return issues_controller.report_issue_control(workstation_id)


@issues_bp.get("/pc-issues")
@issues_bp.get("/reports/issues")
@token_required
@role_required("Admin", "Instructor", "Student")
def list_issues():
    return issues_controller.list_issues_control()


@issues_bp.put("/pc-issues/<int:issue_id>")
@token_required
@role_required("Admin", "Instructor")
def update_issue(issue_id):
    return issues_controller.update_issue_control(issue_id)
