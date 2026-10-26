# frozen_string_literal: true

class Charger
  def call(order)
    gateway.charge!(order)
  rescue Gateway::Declined => e
    order.mark_declined!(e.message)
  end
end
