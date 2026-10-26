package sessions

type Store struct {
	m sync.Map
}

func (s *Store) Set(id string, v *Session) { s.m.Store(id, v) }
