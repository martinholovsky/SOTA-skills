package repo

func (r *Repo) GetUser(ctx context.Context, id int64) (*User, error) {
	row := r.db.QueryRowContext(ctx, "SELECT id, name FROM users WHERE id = $1", id)
	var u User
	return &u, row.Scan(&u.ID, &u.Name)
}
