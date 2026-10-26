package config

func save(path string, data []byte) error {
	return os.WriteFile(path, data, 0644)
}
