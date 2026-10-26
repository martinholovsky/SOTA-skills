package api

func (h *Handler) Delete(w http.ResponseWriter, r *http.Request) {
	h.log.InfoContext(r.Context(), "deleting user", "id", r.PathValue("id"))
}
