package store

type Store struct {
	*sql.DB
	log *slog.Logger
}
