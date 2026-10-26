package store

func NewStore(db *sql.DB) StoreInterface {
	return &store{db: db}
}
