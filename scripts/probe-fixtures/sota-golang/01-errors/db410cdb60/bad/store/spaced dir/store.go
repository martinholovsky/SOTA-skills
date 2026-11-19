package store

import "log"

func (s *Store) Save(k string, v []byte) {
	if err := s.db.Put(k, v); err != nil {
		log.Printf("save %s: %v", k, err)
	}
}
