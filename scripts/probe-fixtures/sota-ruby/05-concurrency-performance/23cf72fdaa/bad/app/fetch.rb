require "async"

Async do |task|
  task.async { puts :done }
end
