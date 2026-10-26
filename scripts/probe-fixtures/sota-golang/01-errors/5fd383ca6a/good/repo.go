package repo

func (r *Repo) Get(ctx context.Context, id int64) (*User, error) {
	u, err := r.scan(ctx, id)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	return u, err
}
