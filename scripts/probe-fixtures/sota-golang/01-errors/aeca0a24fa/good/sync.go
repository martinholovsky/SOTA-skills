package sync

func handle(err error) bool {
	if errors.Is(err, fs.ErrNotExist) {
		return true
	}
	return false
}
