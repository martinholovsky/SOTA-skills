package api

func (h *Handler) Preview(w http.ResponseWriter, r *http.Request) {
	resp, err := h.client.Get(r.URL.Query().Get("url"))
	if err != nil {
		http.Error(w, "fetch failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	io.Copy(w, resp.Body)
}
