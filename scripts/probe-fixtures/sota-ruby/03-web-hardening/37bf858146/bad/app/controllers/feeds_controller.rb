# frozen_string_literal: true

def show
  body = Net::HTTP.get(URI(params[:url]))
end
