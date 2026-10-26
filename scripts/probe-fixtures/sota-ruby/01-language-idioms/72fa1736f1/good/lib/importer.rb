# frozen_string_literal: true

def import(row)
  Parser.parse(row)
rescue Parser::Error
  raise ImportError, "row could not be parsed"
end
