package api

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	var in CreateRequest
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	if err := dec.Decode(&in); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	h.create(r.Context(), in)
}
