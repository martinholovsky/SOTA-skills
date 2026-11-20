# frozen_string_literal: true

def pipeline
  jobs = SizedQueue.new(100)
  jobs
end
