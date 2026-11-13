Creds = Data.define(:user, :password) do
  def inspect = "#<data Creds [REDACTED]>"
  def to_s = inspect
  def pretty_print(q) = q.text(inspect)
end
