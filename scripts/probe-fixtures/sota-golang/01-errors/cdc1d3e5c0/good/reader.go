package feed

func done(err error) bool {
	return errors.Is(err, io.EOF)
}
