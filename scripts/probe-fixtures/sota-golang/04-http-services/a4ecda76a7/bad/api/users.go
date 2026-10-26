package api

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	id := h.svc.Create(r.Context())
	slog.Info("user created", "id", id)
}
