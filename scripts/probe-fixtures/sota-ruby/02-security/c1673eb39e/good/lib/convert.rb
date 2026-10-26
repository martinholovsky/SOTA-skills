# frozen_string_literal: true

require "open3"

def convert(src)
  Open3.capture3("pandoc", "--", src, "-o", "out.pdf")
end
