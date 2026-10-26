# frozen_string_literal: true

class ExportController < ApplicationController
  FIELDS = { "name" => :name, "email" => :email }.freeze

  def index
    render json: User.all.map(&FIELDS.fetch(params[:field]))
  end
end
