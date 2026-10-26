package api

func routes(admin http.Handler) *http.ServeMux {
	mux := http.NewServeMux()
	mux.Handle("/admin/", requireAdmin(admin))
	return mux
}
