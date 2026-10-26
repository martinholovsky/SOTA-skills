package app

type App struct{ db *sql.DB }

func New(dsn string) (*App, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	return &App{db: db}, nil
}
