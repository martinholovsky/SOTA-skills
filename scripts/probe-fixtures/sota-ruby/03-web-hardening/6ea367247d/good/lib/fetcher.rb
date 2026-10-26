# frozen_string_literal: true

def fetch(uri, vetted)
  Net::HTTP.start(uri.host, uri.port, nil, ipaddr: vetted, use_ssl: true) { |http| http.get(uri.request_uri) }
end
