package store

type Store struct {
	db  *sql.DB
	log *slog.Logger
}
