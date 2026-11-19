class ChargeJob
  def perform(order_id)
    Order.find(order_id).charge!
  end
end
