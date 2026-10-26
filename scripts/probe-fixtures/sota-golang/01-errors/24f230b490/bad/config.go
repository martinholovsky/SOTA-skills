package app

func load(path string) error {
	if _, err := os.ReadFile(path); err != nil {
		return fmt.Errorf("load config %s: %v", path, err)
	}
	return nil
}
