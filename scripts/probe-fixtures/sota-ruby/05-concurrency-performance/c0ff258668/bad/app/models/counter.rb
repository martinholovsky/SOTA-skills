class Counter
  @@hits = 0
  def self.bump = @@hits += 1
end
