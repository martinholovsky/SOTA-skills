class TokenFactory
  def self.build
    new
  end

  private

  def self.secret
    "x"
  end
end
