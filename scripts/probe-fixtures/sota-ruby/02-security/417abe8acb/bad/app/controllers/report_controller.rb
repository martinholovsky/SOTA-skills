# frozen_string_literal: true

def show
  render json: Report.new.send(params[:kind])
end
