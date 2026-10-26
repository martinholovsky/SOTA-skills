# frozen_string_literal: true

class TokenFactory
  def self.build
    new(secret)
  end

  private

  def self.secret
    ENV.fetch("TOKEN_SECRET")
  end
end
