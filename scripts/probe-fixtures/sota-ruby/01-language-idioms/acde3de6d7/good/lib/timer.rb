started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
run_job
elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
cutoff = Time.now - 3600
