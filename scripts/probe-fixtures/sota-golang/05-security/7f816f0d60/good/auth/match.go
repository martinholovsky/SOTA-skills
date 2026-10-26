package auth

func matchesUser(pattern, user string) bool {
	return regexp.MustCompile("^" + regexp.QuoteMeta(user) + "$").MatchString(pattern)
}
