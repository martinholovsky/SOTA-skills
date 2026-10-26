# frozen_string_literal: true

def cents(amount)
  (BigDecimal(amount) * 100).round(0, BigDecimal::ROUND_HALF_EVEN).to_i
end
