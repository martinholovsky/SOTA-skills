package sessions

type Store struct {
	mu sync.Mutex
	m  map[string]*Session
}

func (s *Store) Set(id string, v *Session) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.m[id] = v
}
