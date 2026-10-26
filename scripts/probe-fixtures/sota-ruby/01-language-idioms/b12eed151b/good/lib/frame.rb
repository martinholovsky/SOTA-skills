# frozen_string_literal: true

def decode(bytes)
  text = bytes.dup.force_encoding(Encoding::UTF_8)
  raise ArgumentError, "invalid UTF-8" unless text.valid_encoding?

  text
end
