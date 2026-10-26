# frozen_string_literal: true

def show
  send_file Pathname.new(UPLOAD_ROOT).join(params[:name])
end
