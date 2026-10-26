# frozen_string_literal: true

def create
  attrs = JSON.parse(request.body.read).slice("sku", "quantity")
  Order.create(attrs)
end
