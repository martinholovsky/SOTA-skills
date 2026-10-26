# frozen_string_literal: true

def checkout(order)
  Order.transaction do
    order.save!
    ReceiptJob.perform_later(order.id)
  end
end
