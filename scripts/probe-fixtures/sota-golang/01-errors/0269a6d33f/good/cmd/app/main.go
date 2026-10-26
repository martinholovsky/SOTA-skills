package main

import "log"

func main() {
	if err := run(); err != nil {
		log.Printf("run: %v", err)
	}
}
