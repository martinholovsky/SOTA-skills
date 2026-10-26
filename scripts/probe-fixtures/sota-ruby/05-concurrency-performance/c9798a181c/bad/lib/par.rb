r = Ractor.new { Ractor.yield compute }
value = r.take
