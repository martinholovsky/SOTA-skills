package main

import "log"

func main() {
	if _, err := config.Load("app.toml"); err != nil {
		log.Fatal(err)
	}
}
