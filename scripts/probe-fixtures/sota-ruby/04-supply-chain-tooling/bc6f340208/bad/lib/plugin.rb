# frozen_string_literal: true

def run(code)
  eval(code) # rubocop:disable Security/Eval
end
