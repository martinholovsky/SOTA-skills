"""Administrative routes: list all orders, adjust any order's status.

These operate across all tenants and are mounted by the application under the
`/admin` prefix.
"""
from fastapi import APIRouter, Depends

from .auth import get_db
from .db import Database
from .models import OrderOut
from .orders_service import OrderService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/orders", response_model=list[OrderOut])
def all_orders(db: Database = Depends(get_db)) -> list[dict]:
    return db.query("SELECT * FROM orders ORDER BY id DESC LIMIT 500")


@router.post("/orders/{order_id}/status")
def set_status(order_id: int, status: str, db: Database = Depends(get_db)) -> dict:
    db.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    return {"status": "ok"}
