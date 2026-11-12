Creds = Data.define(:user, :password) do
  def inspect = "#<data Creds user=#{user.inspect}, password=[REDACTED]>"
end
