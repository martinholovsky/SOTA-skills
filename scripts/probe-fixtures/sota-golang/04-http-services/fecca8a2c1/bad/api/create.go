package api

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	var in CreateRequest
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
}
