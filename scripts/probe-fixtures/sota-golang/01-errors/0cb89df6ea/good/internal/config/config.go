package config

import (
	"fmt"
	"os"
)

func Load(path string) ([]byte, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}
	return b, nil
}
