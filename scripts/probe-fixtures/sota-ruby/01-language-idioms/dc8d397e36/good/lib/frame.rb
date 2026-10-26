# frozen_string_literal: true

def decode(bytes)
  bytes.encode(Encoding::UTF_8, Encoding::UTF_8, invalid: :replace, undef: :replace)
end
