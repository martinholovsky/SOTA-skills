package store

type StoreInterface interface {
	Get(ctx context.Context, id string) (*User, error)
}

type storeImpl struct{ db *sql.DB }
