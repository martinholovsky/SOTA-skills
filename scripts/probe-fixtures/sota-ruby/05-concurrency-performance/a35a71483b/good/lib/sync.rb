# frozen_string_literal: true

def sync_all(items)
  items.map { |i| Thread.new { sync(i) } }.each(&:join)
end
