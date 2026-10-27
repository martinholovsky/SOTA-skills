require "zlib"

module ZBind
  def self.crc32(data)
    Zlib.crc32(data)
  end
end
