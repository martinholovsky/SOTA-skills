package main

func main() {
	srv := &http.Server{Addr: ":8080", Handler: routes(), ReadHeaderTimeout: 5 * time.Second}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
