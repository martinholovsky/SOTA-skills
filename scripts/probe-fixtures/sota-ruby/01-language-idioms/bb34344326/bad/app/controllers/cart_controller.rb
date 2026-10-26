# frozen_string_literal: true

class CartController < ApplicationController
  def update
    qty = params[:qty].to_i
    cart.set(params[:sku], qty)
  end
end
