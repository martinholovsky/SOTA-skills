package stats

type Stats struct{ hits int64 }

func (s *Stats) Hit() { atomic.AddInt64(&s.hits, 1) }
