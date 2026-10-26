package store

type Store struct{ db *sql.DB }

func (s *Store) Get(ctx context.Context, id string) (*User, error) { return s.get(ctx, id) }
