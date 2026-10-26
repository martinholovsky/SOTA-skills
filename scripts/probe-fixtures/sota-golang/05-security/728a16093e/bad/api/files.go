package api

func (h *Handler) Download(w http.ResponseWriter, r *http.Request) {
	f, err := os.Open(filepath.Join(h.baseDir, r.PathValue("file")))
	if err != nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	defer f.Close()
	io.Copy(w, f)
}
