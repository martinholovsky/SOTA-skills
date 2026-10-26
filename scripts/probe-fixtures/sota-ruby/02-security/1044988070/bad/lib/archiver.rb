# frozen_string_literal: true

require "shellwords"

def archive(out, dir)
  system("tar czf #{Shellwords.escape(out)} #{Shellwords.escape(dir)}")
end
