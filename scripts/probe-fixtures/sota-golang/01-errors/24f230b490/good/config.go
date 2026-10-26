package app

func load(path string) error {
	if _, err := os.ReadFile(path); err != nil {
		return fmt.Errorf("load config %s: %w", path, err)
	}
	return nil
}
