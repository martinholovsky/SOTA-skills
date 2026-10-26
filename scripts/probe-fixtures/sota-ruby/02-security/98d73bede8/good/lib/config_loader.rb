# frozen_string_literal: true

def load_config(text)
  YAML.safe_load(text)
end
