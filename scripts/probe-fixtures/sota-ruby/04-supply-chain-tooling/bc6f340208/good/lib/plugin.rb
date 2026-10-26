# frozen_string_literal: true

def run(name)
  PLUGINS.fetch(name).call
end
