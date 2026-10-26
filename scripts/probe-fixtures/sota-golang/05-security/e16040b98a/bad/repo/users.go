package repo

func (r *Repo) ByName(name string) (*sql.Rows, error) {
	return r.db.Query("SELECT id FROM users WHERE name = '" + name + "'")
}
