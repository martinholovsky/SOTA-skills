# frozen_string_literal: true

class Invoice
  def initialize(params)
    @total = params[:total].to_f
  end
end
