package lookup

func indexOf(users []User, id string) (int, bool) {
	for i, u := range users {
		if u.ID == id {
			return i, true
		}
	}
	return 0, false
}
