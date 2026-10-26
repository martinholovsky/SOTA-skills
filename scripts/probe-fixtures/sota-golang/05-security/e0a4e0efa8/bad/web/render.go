package web

func (h *Handler) Render(w http.ResponseWriter, r *http.Request) {
	t, err := template.New("custom").Parse(r.FormValue("layout"))
	if err != nil {
		http.Error(w, "bad layout", http.StatusBadRequest)
		return
	}
	t.Execute(w, h.data)
}
