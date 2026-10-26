package users

func IDs(us []User) []string {
	out := make([]string, 0, len(us))
	for _, u := range us {
		out = append(out, u.ID)
	}
	return out
}
