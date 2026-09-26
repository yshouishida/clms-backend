CREATE DATABASE clms_db;

USE clms_db;


SELECT
    s.id,
    s.student_number,
    u.first_name,
    u.last_name,
    s.program,
    s.year_level,
    s.section
FROM tblStudents s
INNER JOIN tblUsers u
ON s.user_id = u.id;

  
  

s.student_number
u.first_name
u.last_name
s.program
s.year_level
s.section


u.account_id

u.username
u.password_hash


u.first_name
u.last_name
u.email


u.role_id
u.status
u.created_at
u.date_disabled


s.student_number
s.program
s.year_level
s.section


tblUsers u
tblStudents s


CREATE VIEW vwStudentProfiles AS

SELECT
    s.id AS student_id,
    u.id AS user_id,
    u.account_id,
    u.first_name,
    u.last_name,
    u.email,
    u.username,
    u.role_name,
    u.status AS account_status,
    s.student_number,
    s.program,
    s.yearlevel,
    s.section
FROM tblStudents s
INNER JOIN tblUsers u
    ON s.user_id = u.id,
INNER JOIN tblRoles r
    ON r.id = u.role_id;

    
