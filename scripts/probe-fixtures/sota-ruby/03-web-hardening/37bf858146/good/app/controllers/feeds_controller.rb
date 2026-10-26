# frozen_string_literal: true

RATES_URI = URI("https://rates.example.com/v1/latest")

def show
  body = Net::HTTP.get(RATES_URI)
end
