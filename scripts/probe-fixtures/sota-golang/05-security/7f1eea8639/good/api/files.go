package api

func Open(baseDir, name string) (*os.File, error) {
	root, err := os.OpenRoot(baseDir)
	if err != nil {
		return nil, err
	}
	return root.Open(name)
}
