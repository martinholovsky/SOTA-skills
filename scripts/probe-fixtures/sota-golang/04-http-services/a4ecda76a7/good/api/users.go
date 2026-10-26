package api

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	id := h.svc.Create(r.Context())
	slog.InfoContext(r.Context(), "user created", "id", id)
}
