from backend.repositories import workspace_search_repository as repo
from backend.services.folders_service import student_transaction
from backend.utils.folder_errors import FolderError


def search_workspace_service(user_id, query, kind="all", limit=50, offset=0):
    if not isinstance(query, str):
        raise FolderError("q must be text.", 400)
    query = query.strip()
    if not query or len(query) > 100:
        raise FolderError("q must contain 1 to 100 characters.", 400)
    if kind not in {"all", "folder", "project", "file"}:
        raise FolderError("kind must be all, folder, project, or file.", 400)

    with student_transaction(user_id) as (cursor, student_id):
        rows = repo.search_workspace_repo(
            cursor, student_id, query, kind, limit, offset
        )
        results = []
        for row in rows[:limit]:
            item = dict(row)
            value = item.get("updated_at")
            if value is not None and hasattr(value, "isoformat"):
                item["updated_at"] = value.isoformat()
            results.append(item)
        return {
            "results": results,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(rows) > limit,
            },
        }