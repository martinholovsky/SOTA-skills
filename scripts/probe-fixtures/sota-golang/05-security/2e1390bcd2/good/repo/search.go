package repo

func Search(ctx context.Context, db *sql.DB, name string) {
	_, _ = db.QueryContext(ctx, "SELECT id FROM users WHERE name = $1", name)
}
