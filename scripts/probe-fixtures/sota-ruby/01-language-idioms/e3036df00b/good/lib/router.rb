# frozen_string_literal: true

def route(event, expected)
  case event
  in {status: ^expected}
    :match
  else
    :other
  end
end
