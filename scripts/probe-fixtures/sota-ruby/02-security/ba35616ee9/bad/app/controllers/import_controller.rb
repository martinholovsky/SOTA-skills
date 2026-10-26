# frozen_string_literal: true

def create
  data = URI.open(params[:url]).read
end
