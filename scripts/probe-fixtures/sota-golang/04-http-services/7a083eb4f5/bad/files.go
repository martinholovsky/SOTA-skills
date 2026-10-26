package files

func Get(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join("uploads", r.PathValue("name")))
}
