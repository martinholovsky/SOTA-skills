# frozen_string_literal: true

module Billing
  API_URL = "https://billing.internal"
  private_constant :API_URL
  SIGNING_SALT = "billing-v1"
  private_constant :SIGNING_SALT

  def self.url
    API_URL
  end
end
