package main

func routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServerFS(noListing{staticFS})))
	return mux
}
