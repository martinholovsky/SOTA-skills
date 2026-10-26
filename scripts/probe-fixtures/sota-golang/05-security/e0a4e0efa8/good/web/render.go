package web

//go:embed templates/*.html
var templates embed.FS

var pages = template.Must(template.ParseFS(templates, "templates/*.html"))

func (h *Handler) Render(w http.ResponseWriter, r *http.Request) {
	pages.ExecuteTemplate(w, "layout.html", h.data)
}
