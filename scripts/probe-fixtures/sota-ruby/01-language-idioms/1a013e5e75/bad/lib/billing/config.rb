# frozen_string_literal: true

module Billing
  API_URL = "https://billing.internal"
  SIGNING_SALT = "billing-v1"

  def self.url
    API_URL
  end
end
