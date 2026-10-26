package api

type Handler struct{ up string }

func (h *Handler) Proxy(w http.ResponseWriter, r *http.Request) {
	c := &http.Client{Timeout: 5 * time.Second}
	_, _ = c.Get(h.up)
}
