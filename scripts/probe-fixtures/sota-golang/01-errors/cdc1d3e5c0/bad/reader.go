package feed

func done(err error) bool {
	return err.Error() == "EOF"
}
