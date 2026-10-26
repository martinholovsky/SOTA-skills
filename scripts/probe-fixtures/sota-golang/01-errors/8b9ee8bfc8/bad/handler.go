package api

func (h *Handler) Get(w http.ResponseWriter, r *http.Request) {
	u, err := h.repo.Get(r.Context(), r.PathValue("id"))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, u)
}
