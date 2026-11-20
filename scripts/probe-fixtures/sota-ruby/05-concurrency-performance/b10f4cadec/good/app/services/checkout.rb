# frozen_string_literal: true

def after_checkout(order_id)
  ReceiptJob.perform_later(order_id)
end
