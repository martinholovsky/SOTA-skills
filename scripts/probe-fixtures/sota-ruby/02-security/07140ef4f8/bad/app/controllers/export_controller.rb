# frozen_string_literal: true

class ExportController < ApplicationController
  def index
    render json: User.all.map(&params[:field].to_sym)
  end
end
