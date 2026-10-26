require_relative "app"

use Rack::Session::Cookie, secrets: [ENV.fetch("SESSION_SECRET")], serialize_json: true
run App
