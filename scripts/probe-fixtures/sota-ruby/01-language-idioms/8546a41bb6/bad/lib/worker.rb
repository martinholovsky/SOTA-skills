# frozen_string_literal: true

def run
  loop { process(queue.pop) }
rescue Exception => e
  log(e)
end
