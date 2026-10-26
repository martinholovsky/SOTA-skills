# frozen_string_literal: true

def import(row)
  Parser.parse(row)
rescue Parser::Error => e
  raise e.message
end
