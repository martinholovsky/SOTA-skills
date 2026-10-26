# frozen_string_literal: true

def run
  loop { process(queue.pop) }
rescue StandardError => e
  log(e)
  raise
end
