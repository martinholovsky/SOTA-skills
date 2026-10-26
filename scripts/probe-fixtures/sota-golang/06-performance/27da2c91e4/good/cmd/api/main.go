package main

func main() {
	mux := http.NewServeMux()
	mux.Handle("/v1/", api.Routes())
	mux.Handle("/metrics", promhttp.Handler())
	log.Fatal(http.ListenAndServe(":8080", mux))
}
