package main

func main() {
	srv := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}
	_ = srv.ListenAndServe()
}
