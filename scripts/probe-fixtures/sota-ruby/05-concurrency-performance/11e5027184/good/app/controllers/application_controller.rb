# frozen_string_literal: true

class ApplicationController < ActionController::Base
  before_action { Current.tenant_id = request.headers["X-Tenant"] }
end
