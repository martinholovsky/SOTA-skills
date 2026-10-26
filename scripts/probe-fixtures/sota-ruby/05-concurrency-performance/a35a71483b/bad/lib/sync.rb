# frozen_string_literal: true

def sync_all(items)
  items.each { |i| Thread.new { sync(i) } }
end
