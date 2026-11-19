package store

import "fmt"

func (s *Store) Save(k string, v []byte) error {
	if err := s.db.Put(k, v); err != nil {
		return fmt.Errorf("save %s: %w", k, err)
	}
	return nil
}
