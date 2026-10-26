package sync

func handle(err error) bool {
	if strings.Contains(err.Error(), "no such file") {
		return true
	}
	return false
}
