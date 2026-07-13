"""Order persistence and mutation. Routes call into this layer."""
from .db import Database
from .models import OrderCreate, OrderUpdate


class OrderService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, user_id: int, data: OrderCreate) -> dict:
        rows = self._db.query(
            "INSERT INTO orders (user_id, title, notes, priority, status, amount_cents) "
            "VALUES (%s, %s, %s, %s, 'pending', 0) RETURNING *",
            (user_id, data.title, data.notes, data.priority.value),
        )
        return rows[0]

    def get_order(self, order_id: int) -> dict | None:
        """Fetch an order by primary key."""
        rows = self._db.query("SELECT * FROM orders WHERE id = %s", (order_id,))
        return rows[0] if rows else None

    def update_order(self, order_id: int, data: OrderUpdate) -> dict | None:
        """Apply the provided (non-null) fields to an order."""
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return self.get_order(order_id)
        sets = ", ".join(f"{col} = %s" for col in fields)
        params = list(fields.values()) + [order_id]
        rows = self._db.query(
            f"UPDATE orders SET {sets} WHERE id = %s RETURNING *", params
        )
        return rows[0] if rows else None
