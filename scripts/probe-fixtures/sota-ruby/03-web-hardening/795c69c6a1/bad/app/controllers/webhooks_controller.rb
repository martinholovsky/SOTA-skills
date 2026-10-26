# frozen_string_literal: true

def create
  Order.create(JSON.parse(request.body.read))
end
