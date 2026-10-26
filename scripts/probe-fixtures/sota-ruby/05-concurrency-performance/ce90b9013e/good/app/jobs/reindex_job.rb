# frozen_string_literal: true

def perform
  Product.find_each(&:reindex!)
end
