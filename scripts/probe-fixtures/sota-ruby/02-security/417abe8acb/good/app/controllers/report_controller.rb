# frozen_string_literal: true

KINDS = { "daily" => :daily, "weekly" => :weekly }.freeze

def show
  render json: Report.new.public_send(KINDS.fetch(params[:kind]))
end
