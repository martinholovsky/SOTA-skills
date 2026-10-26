# frozen_string_literal: true

class TokenFactory
  def self.build
    new(secret)
  end

  def self.secret
    ENV.fetch("TOKEN_SECRET")
  end
  private_class_method :secret
end
