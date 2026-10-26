# frozen_string_literal: true

def decode(body)
  JSON.load(body)
end
