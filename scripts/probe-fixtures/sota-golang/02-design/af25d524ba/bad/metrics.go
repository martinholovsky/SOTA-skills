package metrics

func observe(start time.Time) {
	elapsed := time.Now().UnixMilli() - start.UnixMilli()
	latency.Observe(float64(elapsed))
}
