Creds = Data.define(:user, :password) do
  def inspect = "#<data Creds user=#{user.inspect}, password=[REDACTED]>"
  alias_method :to_s, :inspect
  def pretty_print(q) = q.text(inspect)
end
