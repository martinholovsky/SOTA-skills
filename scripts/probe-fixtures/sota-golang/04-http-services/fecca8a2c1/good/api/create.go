package api

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	var in CreateRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&in); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
}
