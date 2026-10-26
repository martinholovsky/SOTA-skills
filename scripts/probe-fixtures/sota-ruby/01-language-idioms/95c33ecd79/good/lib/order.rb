# frozen_string_literal: true

# typed: strict
class Order
  extend T::Sig

  sig { params(attrs: T::Hash[Symbol, Integer]).returns(Order) }
  def self.build(attrs) = new(**attrs)
end
