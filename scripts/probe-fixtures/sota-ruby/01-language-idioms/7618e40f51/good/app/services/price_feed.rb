# frozen_string_literal: true

require "bigdecimal"

class PriceFeed
  def parse(body)
    JSON.parse(body, decimal_class: BigDecimal).fetch("price")
  end
end
