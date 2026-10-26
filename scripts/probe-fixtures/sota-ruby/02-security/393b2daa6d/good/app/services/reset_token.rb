# frozen_string_literal: true

require "securerandom"

def generate
  SecureRandom.urlsafe_base64(32)
end
