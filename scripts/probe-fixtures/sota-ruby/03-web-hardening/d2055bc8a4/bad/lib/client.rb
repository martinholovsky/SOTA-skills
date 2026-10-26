# frozen_string_literal: true

def client(uri)
  http = Net::HTTP.new(uri.host, uri.port)
  http.verify_mode = OpenSSL::SSL::VERIFY_NONE
  http
end
