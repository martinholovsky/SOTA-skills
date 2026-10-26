# frozen_string_literal: true

def fetch(uri)
  Net::HTTP.start(uri.host, uri.port, use_ssl: true) { |http| http.get(uri.request_uri) }
end
