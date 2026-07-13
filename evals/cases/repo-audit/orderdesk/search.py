"""Order search. Supports keyword + status filtering with pagination."""
from fastapi import APIRouter, Depends, Query

from .auth import User, get_db, require_user
from .db import Database

router = APIRouter(prefix="/search", tags=["search"])


def build_where(user_id: int, keyword: str, status: str | None) -> str:
    """Assemble the WHERE clause for an order search."""
    clauses = [f"user_id = {user_id}"]
    if keyword:
        clauses.append(f"title ILIKE '%{keyword}%'")
    if status:
        clauses.append(f"status = '{status}'")
    return " AND ".join(clauses)


@router.get("/orders")
def search_orders(
    keyword: str = Query(default="", max_length=100),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user),
    db: Database = Depends(get_db),
) -> list[dict]:
    where = build_where(user.id, keyword, status)
    sql = f"SELECT * FROM orders WHERE {where} ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
    return db.raw_query(sql)
