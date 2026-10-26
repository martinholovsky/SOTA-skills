# frozen_string_literal: true

def authenticate!
  head :unauthorized unless ActiveSupport::SecurityUtils.secure_compare(request.headers["X-Api-Key"].to_s, API_KEY)
end
