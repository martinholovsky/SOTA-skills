# frozen_string_literal: true

class Order < ApplicationRecord
  after_create_commit :send_receipt

  def send_receipt
    ReceiptJob.perform_later(id)
  end
end
