from backend.repositories.instructors_repository import (
    get_instructiors_repo,
    get_by_id_repo
)



def get_instructors_servie():
    instructors = get_instructiors_repo()

    if instructors is None:
        return None

    return instructors

def get_by_id_service(id):
    instructor =  get_by_id_repo(id)

    if instructor is None:
        return None

    return instructor
