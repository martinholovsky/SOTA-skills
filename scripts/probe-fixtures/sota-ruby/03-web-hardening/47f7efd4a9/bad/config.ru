require_relative "app"

use Rack::Protection, :authenticity_token
run App
