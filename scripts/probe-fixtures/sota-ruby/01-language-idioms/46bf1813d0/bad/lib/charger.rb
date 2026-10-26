# frozen_string_literal: true

class Charger
  def call(order)
    gateway.charge!(order)
  rescue => e
  end
end
