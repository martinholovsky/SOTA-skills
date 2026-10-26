# frozen_string_literal: true

def load_doc(text)
  YAML.safe_load(text)
end
