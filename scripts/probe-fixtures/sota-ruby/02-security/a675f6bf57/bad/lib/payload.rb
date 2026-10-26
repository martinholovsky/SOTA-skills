# frozen_string_literal: true

def decode(body)
  JSON.parse(body, create_additions: true)
end
