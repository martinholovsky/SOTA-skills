# frozen_string_literal: true

def read(blob)
  Marshal.load(blob)
end
