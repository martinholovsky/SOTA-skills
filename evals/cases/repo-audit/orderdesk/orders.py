"""Order routes. Auth is enforced via the require_user dependency."""
from fastapi import APIRouter, Depends, HTTPException

from .auth import User, get_db, require_user
from .db import Database
from .http_client import fetch
from .models import OrderCreate, OrderOut, OrderUpdate
from .orders_service import OrderService
from .ratelimit import limiter

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
def create_order(
    data: OrderCreate,
    user: User = Depends(require_user),
    db: Database = Depends(get_db),
) -> dict:
    limiter.check(f"orders:create:{user.id}")
    order = OrderService(db).create(user.id, data)
    if data.callback_url:
        # Notify the customer's configured integration that the order exists.
        fetch(data.callback_url, method="POST", json={"order_id": order["id"]})
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    user: User = Depends(require_user),
    db: Database = Depends(get_db),
) -> dict:
    order = OrderService(db).get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="not found")
    return order


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    data: OrderUpdate,
    user: User = Depends(require_user),
    db: Database = Depends(get_db),
) -> dict:
    order = OrderService(db).update_order(order_id, data)
    if order is None:
        raise HTTPException(status_code=404, detail="not found")
    return order
