require 'zip'
def unzip(zip, dest)
  root = File.expand_path(dest)
  Zip::File.open(zip) do |z|
    z.each do |e|
      path = File.expand_path(e.name, root)
      raise 'zip slip' unless path.start_with?(root + File::SEPARATOR)
      e.extract(path)
    end
  end
end
