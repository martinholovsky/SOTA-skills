# frozen_string_literal: true

class ApplicationController < ActionController::Base
  before_action { Thread.current[:tenant_id] = request.headers["X-Tenant"] }
end
