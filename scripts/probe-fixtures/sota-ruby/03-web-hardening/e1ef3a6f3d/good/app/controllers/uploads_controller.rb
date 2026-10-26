# frozen_string_literal: true

def create
  upload = params[:file]
  File.binwrite(File.join(UPLOAD_DIR, File.basename(upload.original_filename)), upload.read)
end
