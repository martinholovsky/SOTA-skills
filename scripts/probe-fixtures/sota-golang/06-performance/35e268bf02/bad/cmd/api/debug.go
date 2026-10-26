package main

func startDebug() {
	go func() {
		slog.Error("debug", "err", http.ListenAndServe("localhost:6060", nil))
	}()
}
