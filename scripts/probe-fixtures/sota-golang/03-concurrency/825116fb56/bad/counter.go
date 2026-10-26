package counter

type Counter struct {
	mu sync.RWMutex
	n  map[string]int
}
