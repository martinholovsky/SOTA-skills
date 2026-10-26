package user

func (u User) Deleted() bool {
	return u.DeletedAt != time.Time{}
}
