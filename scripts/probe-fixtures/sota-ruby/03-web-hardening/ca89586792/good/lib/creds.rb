Credentials = Data.define(:username, :password) do
  def inspect = "#<Credentials username=#{username} password=[FILTERED]>"
end
