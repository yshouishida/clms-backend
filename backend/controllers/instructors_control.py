from backend.utils.api_response import success, error

from backend.services.instructors_service import (
    get_instructors_servie,
    get_by_id_service
)


def get_instructors_control():
    instructors = get_instructors_servie()

    if instructors is None:
        return error("Instructors are not found.", 404)

    return success("Get successfully.", 200, instructors)

def get_by_id_control(id):
    instructor = get_by_id_service(id)

    if instructor is None:
        return error("Instructor is not found.", 404)

    return success("Get successfully.", 200, instructor)