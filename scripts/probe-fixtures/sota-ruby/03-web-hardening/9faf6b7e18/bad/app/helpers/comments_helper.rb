# frozen_string_literal: true

def plain(body)
  body.gsub(/<[^>]*>/, "")
end
