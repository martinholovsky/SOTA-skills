# frozen_string_literal: true

require "sinatra/base"

class App < Sinatra::Base
  enable :sessions
  use Rack::Protection::AuthenticityToken
end
