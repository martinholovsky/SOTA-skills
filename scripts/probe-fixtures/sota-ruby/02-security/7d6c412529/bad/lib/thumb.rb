# frozen_string_literal: true

def thumb(src, dst)
  system("convert #{src} -resize 200x200 #{dst}")
end
