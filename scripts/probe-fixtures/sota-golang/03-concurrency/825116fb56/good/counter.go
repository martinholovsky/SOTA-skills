package counter

type Counter struct {
	mu sync.Mutex
	n  map[string]int
}
