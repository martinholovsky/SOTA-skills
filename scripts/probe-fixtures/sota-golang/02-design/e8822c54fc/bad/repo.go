package repo

func (r *Repo) Count(ctx context.Context) (int, error) {
	var n int
	err := r.db.QueryRow("SELECT count(*) FROM users").Scan(&n)
	return n, err
}
