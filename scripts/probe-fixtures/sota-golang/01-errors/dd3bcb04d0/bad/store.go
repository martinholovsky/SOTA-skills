package store

func open(path string) error {
	if _, err := os.Open(path); err != nil {
		return fmt.Errorf("failed to open %s: %w", path, err)
	}
	return nil
}
