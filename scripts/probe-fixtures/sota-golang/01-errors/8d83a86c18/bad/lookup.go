package lookup

func indexOf(users []User, id string) int {
	for i, u := range users {
		if u.ID == id {
			return i
		}
	}
	return -1
}
