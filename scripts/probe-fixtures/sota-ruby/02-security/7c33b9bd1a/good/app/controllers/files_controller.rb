# frozen_string_literal: true

def show
  name = File.basename(params[:name].to_s)
  path = Pathname.new(UPLOAD_ROOT).join(name).expand_path
  raise NotFound unless path.to_s.start_with?("#{UPLOAD_ROOT}/")

  send_file path
end
