package metrics

func observe(start time.Time) {
	elapsed := time.Since(start).Milliseconds()
	latency.Observe(float64(elapsed))
}
