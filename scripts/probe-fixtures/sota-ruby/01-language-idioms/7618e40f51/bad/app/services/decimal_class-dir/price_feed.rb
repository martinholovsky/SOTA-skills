# frozen_string_literal: true

class PriceFeed
  def parse(body)
    JSON.parse(body).fetch("price")
  end
end
