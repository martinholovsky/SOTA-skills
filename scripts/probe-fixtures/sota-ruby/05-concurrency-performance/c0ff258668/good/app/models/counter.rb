require 'concurrent'
class Counter
  HITS = Concurrent::AtomicFixnum.new(0)
  def self.bump = HITS.increment
end
