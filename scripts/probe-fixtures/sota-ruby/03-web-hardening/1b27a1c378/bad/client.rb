class Client
  attr_reader :user, :api_key
  def initialize(user, api_key) = (@user, @api_key = user, api_key)
end
