package main

import _ "net/http/pprof" // registers on http.DefaultServeMux

func startDebug() {
	go func() {
		slog.Error("debug", "err", http.ListenAndServe("localhost:6060", nil))
	}()
}
