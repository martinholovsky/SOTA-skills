package config

import (
	"log"
	"os"
)

func Load(path string) []byte {
	b, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("read config: %v", err)
	}
	return b
}
