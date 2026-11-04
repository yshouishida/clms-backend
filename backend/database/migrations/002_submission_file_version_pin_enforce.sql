-- Run only after the DBA has identified and populated the exact version_id
-- for every legacy tblSubmissionFiles row. The diagnostic query reports all
-- unresolved links. If any remain, the ALTER fails and the preparation
-- triggers continue to require version_id on new inserts and updates.

SELECT sf.id AS submission_file_id,
       sf.submission_id,
       sf.file_id,
       s.submitted_at
FROM tblSubmissionFiles AS sf
JOIN tblSubmissions AS s ON s.id = sf.submission_id
WHERE sf.version_id IS NULL
ORDER BY sf.id;

ALTER TABLE tblSubmissionFiles
    MODIFY COLUMN version_id INT NOT NULL;

-- Keep the triggers as defense in depth. The existing
-- UNIQUE (submission_id, file_id) remains unchanged.
