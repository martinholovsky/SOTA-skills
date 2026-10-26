# frozen_string_literal: true

def log_for(ref)
  `git log --oneline #{ref}`
end
