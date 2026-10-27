threads = 2.times.map { Thread.new { puts :done } }
threads.each(&:join)
