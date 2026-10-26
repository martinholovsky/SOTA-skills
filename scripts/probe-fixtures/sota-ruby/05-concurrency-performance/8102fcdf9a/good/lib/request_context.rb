# frozen_string_literal: true

def current_request_id
  Thread.current.thread_variable_get(:request_id)
end
