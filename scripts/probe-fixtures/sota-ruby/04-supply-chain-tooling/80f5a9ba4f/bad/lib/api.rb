# frozen_string_literal: true

def decode(body)
  Oj.load(body)
end
