# frozen_string_literal: true

def current_request_id
  Thread.current[:request_id]
end
