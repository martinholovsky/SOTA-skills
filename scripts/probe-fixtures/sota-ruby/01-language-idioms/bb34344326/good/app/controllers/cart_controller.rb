# frozen_string_literal: true

class CartController < ApplicationController
  def update
    qty = Integer(params[:qty], 10)
    cart.set(params[:sku], qty)
  end
end
