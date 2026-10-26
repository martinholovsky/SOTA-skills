package repo

func (r *Repo) init() error {
	stmt, err := r.db.Prepare("SELECT id, name FROM users WHERE id = $1")
	if err != nil {
		return err
	}
	r.getUser = stmt
	return nil
}
