# frozen_string_literal: true

def parse(body)
  JSON.parse(body, max_nesting: false)
end
