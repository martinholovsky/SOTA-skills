# frozen_string_literal: true

# typed: strict
class Order
  extend T::Sig

  sig { params(attrs: T.untyped).returns(T.untyped) }
  def self.build(attrs) = new(**T.unsafe(attrs))
end
