# frozen_string_literal: true

class Model
  class_eval do
    define_method(:total) { items.sum(&:price) }
  end
end
