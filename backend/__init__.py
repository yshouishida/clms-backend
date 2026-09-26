from flask import Flask



def create_app():
    app = Flask(__name__)

    from backend.routes.instructors_route import instructors_bp
    from backend.routes.student_route import students_bp
    from backend.routes.users_route import users_bp

    app.register_blueprint(instructors_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(users_bp)

    return app


