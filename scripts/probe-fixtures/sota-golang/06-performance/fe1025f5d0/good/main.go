package main

import (
	"log/slog"
	"net/http"
	_ "net/http/pprof"
)

func main() {
	go func() { slog.Error("pprof", "err", http.ListenAndServe("localhost:6060", nil)) }()
	mux := http.NewServeMux()
	http.ListenAndServe(":8080", mux)
}
