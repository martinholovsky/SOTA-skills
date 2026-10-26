package api

func (h *Handler) Export(w http.ResponseWriter, r *http.Request) {
	data := h.store.Render(r.Context(), r.PathValue("id"))
	w.Write(data)
}
