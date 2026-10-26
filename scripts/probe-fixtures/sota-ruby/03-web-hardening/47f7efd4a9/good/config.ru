require_relative "app"

use Rack::Protection, use: [:authenticity_token]
run App
