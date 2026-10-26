# frozen_string_literal: true

def authenticate!
  head :unauthorized unless ActiveSupport::SecurityUtils.fixed_length_secure_compare(request.headers["X-Api-Key"], API_KEY)
end
