package f

func Close(f *os.File) {
	defer f.Close() // nolint:errcheck
}
