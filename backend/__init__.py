from flask import Flask


def create_app():
    app = Flask(__name__)

    from backend.routes.instructors_route import instructors_bp
    from backend.routes.students_route import students_bp
    from backend.routes.users_route import users_bp
    from backend.routes.auth_route import auth_bp
    from backend.routes.folders_route import folders_bp

    app.register_blueprint(instructors_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(folders_bp)

    return app