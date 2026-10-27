require "image_processing/vips"

class Thumbnailer
  def call(path)
    ImageProcessing::Vips.source(path).resize_to_limit(256, 256).call
  end
end
