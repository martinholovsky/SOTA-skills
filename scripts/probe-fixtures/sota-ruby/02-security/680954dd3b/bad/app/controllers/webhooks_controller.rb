# frozen_string_literal: true

def verify!(signature, expected)
  head :unauthorized unless signature == expected
end
