package api

func (h *Handler) Delete(w http.ResponseWriter, r *http.Request) {
	log.Printf("deleting user %s", r.PathValue("id"))
}
