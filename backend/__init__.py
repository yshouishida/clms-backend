from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge
from backend.utils.api_response import error

def create_app():
    app = Flask(__name__)
    app.config["PROJECT_UPLOAD_MAX_FILES"] = 10
    app.config["PROJECT_FILE_MAX_BYTES"] = 20 * 1024 * 1024
    app.config["MAX_CONTENT_LENGTH"] = 21 * 1024 * 1024 # 16MB max file size
    app.config["PROJECT_UPLOAD_MAX_BYTES"] = 100 * 1024 * 1024
    app.config["MAX_CONTENT_LENGTH"] = 101 * 1024 * 1024

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(exc):
     return error("Upload request is too large.", 413)

    

    from backend.routes.instructors_route import instructors_bp
    from backend.routes.students_route import students_bp
    from backend.routes.users_route import users_bp
    from backend.routes.auth_route import auth_bp
    from backend.routes.folders_route import folders_bp
    from backend.routes.projects_route import projects_bp
    from backend.routes.projectFiles_route import project_files_bp
    from backend.routes.project_versions_route import project_versions_bp
    from backend.routes.classes_route import classes_bp
    from backend.routes.activities_route import activities_bp
   

    app.register_blueprint(instructors_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(project_files_bp)
    app.register_blueprint(project_versions_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(activities_bp)
    

    return app


