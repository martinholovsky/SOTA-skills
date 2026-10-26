package api

func (h *Handler) Preview(w http.ResponseWriter, r *http.Request) {
	target, ok := h.feeds[r.URL.Query().Get("feed")]
	if !ok {
		http.Error(w, "unknown feed", http.StatusBadRequest)
		return
	}
	req, _ := http.NewRequestWithContext(r.Context(), http.MethodGet, target, nil)
	resp, err := h.client.Do(req)
	if err != nil {
		http.Error(w, "fetch failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	io.Copy(w, resp.Body)
}
