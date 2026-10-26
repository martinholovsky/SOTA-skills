package store

func NewStore(db *sql.DB) *Store {
	return &Store{db: db}
}
