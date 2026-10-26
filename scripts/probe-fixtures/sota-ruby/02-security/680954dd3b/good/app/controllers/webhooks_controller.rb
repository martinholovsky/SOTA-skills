# frozen_string_literal: true

def verify!(signature, expected)
  head :unauthorized unless Rack::Utils.secure_compare(signature, expected)
end
