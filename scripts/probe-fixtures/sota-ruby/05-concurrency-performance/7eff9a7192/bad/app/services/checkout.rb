# frozen_string_literal: true

def after_checkout(order)
  ReceiptJob.perform_later(order)
end
