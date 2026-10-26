package repo

func (r *Repo) ByName(name string) ([]User, error) {
	var us []User
	err := r.db.Where(fmt.Sprintf("name = '%s'", name)).Find(&us).Error
	return us, err
}
