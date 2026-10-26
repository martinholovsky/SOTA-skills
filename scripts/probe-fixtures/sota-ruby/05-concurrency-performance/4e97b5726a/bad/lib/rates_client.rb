# frozen_string_literal: true

def fetch
  Timeout.timeout(5) { Net::HTTP.get(RATES_URI) }
end
