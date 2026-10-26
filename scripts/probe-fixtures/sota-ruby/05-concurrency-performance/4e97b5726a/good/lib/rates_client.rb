# frozen_string_literal: true

def fetch
  Net::HTTP.start(RATES_URI.host, RATES_URI.port, use_ssl: true, open_timeout: 2, read_timeout: 5) { |h| h.get(RATES_URI.path).body }
end
