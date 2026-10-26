# frozen_string_literal: true

require "open3"

def log_for(ref)
  out, _status = Open3.capture2("git", "log", "--oneline", "--end-of-options", ref)
  out
end
