package api

func (h *Handler) Export(w http.ResponseWriter, r *http.Request) {
	data := h.store.Render(r.Context(), r.PathValue("id"))
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Write(data)
}
