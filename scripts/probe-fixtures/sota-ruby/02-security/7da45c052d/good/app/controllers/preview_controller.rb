# frozen_string_literal: true

def show
  template = ERB.new(File.read(template_file), trim_mode: "-")
  render html: template.result_with_hash(user: current_user)
end
