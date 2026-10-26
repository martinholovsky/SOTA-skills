# frozen_string_literal: true

def show
  send_data File.read(File.join(UPLOAD_DIR, params[:name]))
end
