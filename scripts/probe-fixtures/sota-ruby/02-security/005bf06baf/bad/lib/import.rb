# frozen_string_literal: true

def load_doc(text)
  YAML.unsafe_load(text)
end
