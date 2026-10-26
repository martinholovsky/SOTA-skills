port = Ractor::Port.new
Ractor.new(port) { |p| p << compute }
value = port.receive
first = items.take(5)
