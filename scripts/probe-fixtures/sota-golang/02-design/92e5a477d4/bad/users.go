package users

func Map[T, U any](in []T, f func(T) U) []U {
	out := make([]U, 0, len(in))
	for _, v := range in {
		out = append(out, f(v))
	}
	return out
}

func IDs(us []User) []string { return Map(us, func(u User) string { return u.ID }) }
