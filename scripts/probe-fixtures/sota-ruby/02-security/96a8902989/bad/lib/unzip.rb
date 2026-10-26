require 'zip'
def unzip(zip, dest)
  Zip::File.open(zip) do |z|
    z.each { |e| e.extract(File.join(dest, e.name)) }
  end
end
