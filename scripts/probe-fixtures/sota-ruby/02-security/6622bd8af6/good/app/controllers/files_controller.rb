# frozen_string_literal: true

def show
  path = File.expand_path(File.basename(params[:name].to_s), UPLOAD_DIR)
  raise NotFound unless path.start_with?("#{UPLOAD_DIR}/")

  send_data File.read(path)
end
