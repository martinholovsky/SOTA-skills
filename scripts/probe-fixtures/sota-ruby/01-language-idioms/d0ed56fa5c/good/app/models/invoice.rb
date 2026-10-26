# frozen_string_literal: true

require "bigdecimal"

class Invoice
  def initialize(params)
    @total = BigDecimal(params[:total])
  end
end
