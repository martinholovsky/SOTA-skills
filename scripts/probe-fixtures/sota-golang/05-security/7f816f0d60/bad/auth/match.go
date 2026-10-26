package auth

func matchesUser(pattern, user string) bool {
	return regexp.MustCompile("^" + user + "$").MatchString(pattern)
}
