class Thumbnailer
  def call(path)
    File.binread(path, 12)
  end
end
