# frozen_string_literal: true

require "sinatra/base"

class App < Sinatra::Base
  set :protection, use: [:authenticity_token]
end
