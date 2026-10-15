CREATE TABLE tblSubmissionVersions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    submission_id INT NOT NULL,
    version_number INT NOT NULL,
    submitted_at DATETIME NOT NULL,
    status ENUM('Submitted', 'Late') NOT NULL,
    FOREIGN KEY (submission_id) REFERENCES tblSubmissions (id),
    UNIQUE (submission_id, version_number)
);

CREATE TABLE tblSubmissionVersionFiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    submission_version_id INT NOT NULL,
    project_version_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT NOT NULL,
    FOREIGN KEY (submission_version_id) REFERENCES tblSubmissionVersions (id),
    FOREIGN KEY (project_version_id) REFERENCES tblProjectVersions (id),
    UNIQUE (submission_version_id, project_version_id)
);
