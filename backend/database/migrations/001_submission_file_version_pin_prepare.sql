-- One-time upgrade from Database_Design_V04.sql. Run with a MySQL/MariaDB
-- client that understands DELIMITER. Back up the database before applying.
-- DDL commits independently; do not assume this file is one transaction.
-- Existing tblSubmissionFiles rows remain intact with version_id = NULL.
-- Precondition: these V04 tables use InnoDB so their foreign keys are enforced.
-- Pause direct submission-file writers until both triggers are installed.

-- The parent key makes the composite FK target explicit and unique.
ALTER TABLE tblProjectVersions
    ADD UNIQUE KEY uq_project_versions_file_id_id (file_id, id);

ALTER TABLE tblSubmissionFiles
    ADD COLUMN version_id INT NULL AFTER file_id,
    ADD KEY ix_submission_files_file_version (file_id, version_id),
    ADD CONSTRAINT fk_submission_files_file_version
        FOREIGN KEY (file_id, version_id)
        REFERENCES tblProjectVersions (file_id, id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;

-- A nullable column is necessary while old links are investigated. These
-- triggers require a version on every new link and forbid unpinning an old one.
DELIMITER $$
CREATE TRIGGER trg_submission_files_require_version_insert
BEFORE INSERT ON tblSubmissionFiles
FOR EACH ROW
BEGIN
    IF NEW.version_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'version_id is required for new submission files';
    END IF;
END$$

CREATE TRIGGER trg_submission_files_require_version_update
BEFORE UPDATE ON tblSubmissionFiles
FOR EACH ROW
BEGIN
    IF NEW.version_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'version_id is required when updating submission files';
    END IF;
END$$
DELIMITER ;

-- DBA review report: every unresolved link, with candidate version records.
-- Timestamps and current_path are clues, not proof of the submitted bytes.
-- Resolve from authoritative historical evidence; never choose MAX(id),
-- MAX(version_number), or the current path by default.
SELECT sf.id AS submission_file_id,
       sf.submission_id,
       sf.file_id,
       s.submitted_at,
       f.current_path,
       v.id AS candidate_version_id,
       v.version_number,
       v.created_at AS version_created_at,
       v.file_path AS candidate_file_path
FROM tblSubmissionFiles AS sf
JOIN tblSubmissions AS s ON s.id = sf.submission_id
JOIN tblProjectFiles AS f ON f.id = sf.file_id
LEFT JOIN tblProjectVersions AS v ON v.file_id = sf.file_id
WHERE sf.version_id IS NULL
ORDER BY sf.id, v.version_number, v.id;
