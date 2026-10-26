package upload

func finish(tmp string) error {
	if err := os.Remove(tmp); err != nil {
		return fmt.Errorf("remove temp %s: %w", tmp, err)
	}
	return nil
}
