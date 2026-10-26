# frozen_string_literal: true

def perform
  Product.all.each(&:reindex!)
end
