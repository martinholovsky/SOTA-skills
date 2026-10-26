package stats

type Stats struct{ hits atomic.Int64 }

func (s *Stats) Hit() { s.hits.Add(1) }
