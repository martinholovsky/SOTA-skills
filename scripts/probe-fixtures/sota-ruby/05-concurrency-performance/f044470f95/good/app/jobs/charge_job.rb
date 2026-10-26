class ChargeJob
  def perform(order_id)
    order = Order.find(order_id)
    order.with_lock do
      next if order.charged?
      order.charge!(idempotency_key: "charge-#{order.id}")
    end
  end
end
