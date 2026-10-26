# frozen_string_literal: true

def create
  exporter = params[:type].constantize.new
end
