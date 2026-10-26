package api

func Open(baseDir, name string) (*os.File, error) {
	return os.Open(filepath.Join(baseDir, name))
}
