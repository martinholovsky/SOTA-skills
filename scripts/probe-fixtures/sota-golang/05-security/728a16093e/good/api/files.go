package api

func (h *Handler) Download(w http.ResponseWriter, r *http.Request) {
	f, err := h.root.Open(r.PathValue("file"))
	if err != nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	defer f.Close()
	io.Copy(w, f)
}
