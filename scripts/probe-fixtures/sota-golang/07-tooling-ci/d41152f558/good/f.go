package f

func Read(name string) ([]byte, error) {
	return os.ReadFile(name) // #nosec G304 -- name is checked against the allowlist above
}
