class Svc
  def initialize(token) = (@token = token)
  def inspect = "#<Svc>"
  def pretty_print(q) = q.text(inspect)
end
