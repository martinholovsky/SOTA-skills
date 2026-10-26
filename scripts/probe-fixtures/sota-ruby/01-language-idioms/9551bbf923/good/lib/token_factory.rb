class TokenFactory
  def self.build
    new
  end

  def self.secret
    "x"
  end
  private_class_method :secret
end
