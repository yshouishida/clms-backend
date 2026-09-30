-- Run after creating the tables in the supplied schema.
-- These views preserve historical and inactive rows; filter status in queries as needed.
-- User password hashes are deliberately excluded.

CREATE OR REPLACE VIEW vw_users_with_roles AS
SELECT
    u.id AS user_id,
    u.account_id,
    u.first_name,
    u.last_name,
    u.email,
    u.username,
    u.role_id,
    r.role_name,
    u.status AS user_status,
    u.created_at,
    u.date_disabled
FROM tblUsers AS u
JOIN tblRoles AS r ON r.id = u.role_id;

CREATE OR REPLACE VIEW vw_students AS
SELECT
    s.id AS student_id,
    s.user_id,
    s.student_number,
    u.account_id,
    u.first_name,
    u.last_name,
    u.email,
    u.status AS user_status,
    s.program,
    s.year_level,
    s.section
FROM tblStudents AS s
JOIN tblUsers AS u ON u.id = s.user_id;

CREATE OR REPLACE VIEW vw_instructors AS
SELECT
    i.id AS instructor_id,
    i.user_id,
    i.employee_number,
    u.account_id,
    u.first_name,
    u.last_name,
    u.email,
    u.status AS user_status
FROM tblInstructors AS i
JOIN tblUsers AS u ON u.id = i.user_id;

CREATE OR REPLACE VIEW vw_rfid_assignments AS
SELECT
    a.id AS assignment_id,
    a.rfid_id,
    c.card_uid,
    c.status AS card_status,
    a.student_id,
    s.student_number,
    u.first_name AS student_first_name,
    u.last_name AS student_last_name,
    a.assigned_at,
    a.unassigned_at,
    a.status AS assignment_status
FROM tblRFIDAssignments AS a
JOIN tblRFIDCards AS c ON c.id = a.rfid_id
JOIN tblStudents AS s ON s.id = a.student_id
JOIN tblUsers AS u ON u.id = s.user_id;

CREATE OR REPLACE VIEW vw_classes AS
SELECT
    c.id AS class_id,
    c.class_code,
    c.class_name,
    c.description,
    c.school_year,
    c.semester,
    c.status AS class_status,
    c.created_at,
    c.instructor_id,
    i.employee_number,
    u.first_name AS instructor_first_name,
    u.last_name AS instructor_last_name
FROM tblClasses AS c
JOIN tblInstructors AS i ON i.id = c.instructor_id
JOIN tblUsers AS u ON u.id = i.user_id;

CREATE OR REPLACE VIEW vw_class_members AS
SELECT
    m.id AS class_member_id,
    m.class_id,
    c.class_code,
    c.class_name,
    c.school_year,
    c.semester,
    m.student_id,
    s.student_number,
    u.first_name AS student_first_name,
    u.last_name AS student_last_name,
    m.enrolled_at,
    m.status AS membership_status
FROM tblClassMembers AS m
JOIN tblClasses AS c ON c.id = m.class_id
JOIN tblStudents AS s ON s.id = m.student_id
JOIN tblUsers AS u ON u.id = s.user_id;

CREATE OR REPLACE VIEW vw_activities AS
SELECT
    a.id AS activity_id,
    a.class_id,
    c.class_code,
    c.class_name,
    a.instructor_id,
    u.first_name AS instructor_first_name,
    u.last_name AS instructor_last_name,
    a.activity_name,
    a.instructions,
    a.due_date,
    a.created_at,
    a.status AS activity_status
FROM tblActivities AS a
JOIN tblClasses AS c ON c.id = a.class_id
JOIN tblInstructors AS i ON i.id = a.instructor_id
JOIN tblUsers AS u ON u.id = i.user_id;

CREATE OR REPLACE VIEW vw_folders AS
SELECT
    f.id AS folder_id,
    f.student_id,
    s.student_number,
    f.parent_folder_id,
    parent.folder_name AS parent_folder_name,
    f.folder_name,
    f.created_at,
    f.deleted_at,
    f.status AS folder_status
FROM tblFolders AS f
JOIN tblStudents AS s ON s.id = f.student_id
LEFT JOIN tblFolders AS parent ON parent.id = f.parent_folder_id;

CREATE OR REPLACE VIEW vw_projects AS
SELECT
    p.id AS project_id,
    p.student_id,
    s.student_number,
    p.folder_id,
    f.folder_name,
    p.project_name,
    p.description,
    p.created_at,
    p.updated_at,
    p.deleted_at,
    p.status AS project_status
FROM tblProjects AS p
JOIN tblStudents AS s ON s.id = p.student_id
LEFT JOIN tblFolders AS f ON f.id = p.folder_id;

CREATE OR REPLACE VIEW vw_project_files AS
SELECT
    pf.id AS file_id,
    pf.project_id,
    p.project_name,
    p.student_id AS project_student_id,
    pf.folder_id,
    f.folder_name,
    pf.file_name,
    pf.file_type,
    pf.file_size,
    pf.current_path,
    pf.created_at,
    pf.updated_at,
    pf.deleted_at,
    pf.status AS file_status
FROM tblProjectFiles AS pf
JOIN tblProjects AS p ON p.id = pf.project_id
LEFT JOIN tblFolders AS f ON f.id = pf.folder_id;

CREATE OR REPLACE VIEW vw_project_versions AS
SELECT
    v.id AS version_id,
    v.file_id,
    pf.file_name,
    pf.project_id,
    p.project_name,
    v.version_number,
    v.file_path,
    v.file_size,
    v.created_by AS created_by_user_id,
    u.first_name AS created_by_first_name,
    u.last_name AS created_by_last_name,
    v.created_at
FROM tblProjectVersions AS v
JOIN tblProjectFiles AS pf ON pf.id = v.file_id
JOIN tblProjects AS p ON p.id = pf.project_id
JOIN tblUsers AS u ON u.id = v.created_by;

CREATE OR REPLACE VIEW vw_submissions AS
SELECT
    sub.id AS submission_id,
    sub.activity_id,
    a.activity_name,
    a.class_id,
    c.class_code,
    sub.student_id,
    s.student_number,
    u.first_name AS student_first_name,
    u.last_name AS student_last_name,
    sub.project_id,
    p.project_name,
    sub.submitted_at,
    sub.status AS submission_status,
    sub.remarks
FROM tblSubmissions AS sub
JOIN tblActivities AS a ON a.id = sub.activity_id
JOIN tblClasses AS c ON c.id = a.class_id
JOIN tblStudents AS s ON s.id = sub.student_id
JOIN tblUsers AS u ON u.id = s.user_id
LEFT JOIN tblProjects AS p ON p.id = sub.project_id;

CREATE OR REPLACE VIEW vw_submission_files AS
SELECT
    sf.id AS submission_file_id,
    sf.submission_id,
    sub.activity_id,
    sub.student_id,
    sf.file_id,
    pf.file_name,
    pf.file_type,
    pf.file_size,
    pf.current_path,
    pf.project_id AS file_project_id
FROM tblSubmissionFiles AS sf
JOIN tblSubmissions AS sub ON sub.id = sf.submission_id
JOIN tblProjectFiles AS pf ON pf.id = sf.file_id;

CREATE OR REPLACE VIEW vw_announcements AS
SELECT
    an.id AS announcement_id,
    an.class_id,
    c.class_code,
    c.class_name,
    an.author_id AS author_user_id,
    u.first_name AS author_first_name,
    u.last_name AS author_last_name,
    an.title,
    an.content,
    an.posted_at,
    an.status AS announcement_status
FROM tblAnnouncements AS an
JOIN tblClasses AS c ON c.id = an.class_id
JOIN tblUsers AS u ON u.id = an.author_id;

CREATE OR REPLACE VIEW vw_workstations AS
SELECT
    w.id AS workstation_id,
    w.laboratory_id,
    l.laboratory_name,
    l.room_number,
    l.status AS laboratory_status,
    w.pc_name,
    w.asset_tag,
    w.ip_address,
    w.processor,
    w.ram,
    w.storage,
    w.operating_system,
    w.status AS workstation_status,
    w.`condition` AS workstation_condition
FROM tblWorkstations AS w
JOIN tblLaboratories AS l ON l.id = w.laboratory_id;

CREATE OR REPLACE VIEW vw_rfid_readers AS
SELECT
    r.id AS reader_id,
    r.workstation_id,
    w.pc_name,
    w.laboratory_id,
    r.device_name,
    r.serial_number,
    r.connection_status,
    r.status AS reader_status
FROM tblRFIDReaders AS r
LEFT JOIN tblWorkstations AS w ON w.id = r.workstation_id;

CREATE OR REPLACE VIEW vw_arduino_devices AS
SELECT
    d.id AS arduino_id,
    d.workstation_id,
    w.pc_name,
    w.laboratory_id,
    d.device_name,
    d.serial_port,
    d.connection_status,
    d.status AS device_status
FROM tblArduinoDevices AS d
LEFT JOIN tblWorkstations AS w ON w.id = d.workstation_id;

CREATE OR REPLACE VIEW vw_cameras AS
SELECT
    cam.id AS camera_id,
    cam.workstation_id,
    w.pc_name,
    w.laboratory_id,
    cam.device_name,
    cam.connection_status,
    cam.status AS camera_status
FROM tblCameras AS cam
JOIN tblWorkstations AS w ON w.id = cam.workstation_id;

CREATE OR REPLACE VIEW vw_laboratory_sessions AS
SELECT
    ses.id AS session_id,
    ses.student_id,
    s.student_number,
    u.first_name AS student_first_name,
    u.last_name AS student_last_name,
    ses.workstation_id,
    w.pc_name,
    w.laboratory_id,
    l.laboratory_name,
    ses.rfid_id,
    card.card_uid,
    ses.login_method,
    ses.login_at,
    ses.logout_at,
    ses.status AS session_status
FROM tblLaboratorySessions AS ses
JOIN tblStudents AS s ON s.id = ses.student_id
JOIN tblUsers AS u ON u.id = s.user_id
JOIN tblWorkstations AS w ON w.id = ses.workstation_id
JOIN tblLaboratories AS l ON l.id = w.laboratory_id
LEFT JOIN tblRFIDCards AS card ON card.id = ses.rfid_id;

CREATE OR REPLACE VIEW vw_camera_captures AS
SELECT
    cap.id AS capture_id,
    cap.session_id,
    ses.student_id,
    ses.workstation_id AS session_workstation_id,
    cap.camera_id,
    cam.workstation_id AS camera_workstation_id,
    cam.device_name AS camera_name,
    cap.file_path,
    cap.captured_at,
    cap.capture_status
FROM tblCameraCaptures AS cap
JOIN tblLaboratorySessions AS ses ON ses.id = cap.session_id
JOIN tblCameras AS cam ON cam.id = cap.camera_id;

CREATE OR REPLACE VIEW vw_pc_status AS
SELECT
    ps.id AS pc_status_id,
    ps.workstation_id,
    w.pc_name,
    w.laboratory_id,
    ps.session_id,
    ses.student_id AS session_student_id,
    ses.workstation_id AS session_workstation_id,
    ps.online_status,
    ps.cpu_usage,
    ps.ram_usage,
    ps.storage_usage,
    ps.network_status,
    ps.camera_status,
    ps.rfid_status,
    ps.recorded_at
FROM tblPCStatus AS ps
JOIN tblWorkstations AS w ON w.id = ps.workstation_id
LEFT JOIN tblLaboratorySessions AS ses ON ses.id = ps.session_id;

CREATE OR REPLACE VIEW vw_issue_reports AS
SELECT
    ir.id AS issue_id,
    ir.reported_by AS reporter_user_id,
    reporter.first_name AS reporter_first_name,
    reporter.last_name AS reporter_last_name,
    ir.workstation_id,
    w.pc_name,
    w.laboratory_id,
    ir.session_id,
    ses.workstation_id AS session_workstation_id,
    ir.issue_type,
    ir.title,
    ir.description,
    ir.priority,
    ir.status AS issue_status,
    ir.reported_at,
    ir.resolved_at,
    ir.resolved_by AS resolver_user_id,
    resolver.first_name AS resolver_first_name,
    resolver.last_name AS resolver_last_name,
    ir.resolution_details
FROM tblIssueReports AS ir
JOIN tblUsers AS reporter ON reporter.id = ir.reported_by
JOIN tblWorkstations AS w ON w.id = ir.workstation_id
LEFT JOIN tblLaboratorySessions AS ses ON ses.id = ir.session_id
LEFT JOIN tblUsers AS resolver ON resolver.id = ir.resolved_by;

CREATE OR REPLACE VIEW vw_audit_logs AS
SELECT
    log.id AS audit_log_id,
    log.user_id,
    u.account_id,
    u.first_name,
    u.last_name,
    log.action,
    log.entity_name,
    log.record_id,
    log.description,
    log.ip_address,
    log.created_at
FROM tblAuditLogs AS log
JOIN tblUsers AS u ON u.id = log.user_id;

CREATE OR REPLACE VIEW vw_system_logs AS
SELECT
    log.id AS system_log_id,
    log.workstation_id,
    w.pc_name,
    w.laboratory_id,
    log.log_level,
    log.source,
    log.message,
    log.created_at
FROM tblSystemLogs AS log
LEFT JOIN tblWorkstations AS w ON w.id = log.workstation_id;
