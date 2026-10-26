package repo

func Search(db *sql.DB, name string) {
	q := fmt.Sprintf("SELECT id FROM users WHERE name = '%s'", name)
	_, _ = db.Query(q)
}
