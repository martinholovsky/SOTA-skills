package api

func (h *Handler) Get(w http.ResponseWriter, r *http.Request) {
	u, err := h.repo.Get(r.Context(), r.PathValue("id"))
	if err != nil {
		h.log.ErrorContext(r.Context(), "get user", "err", err)
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	writeJSON(w, u)
}
