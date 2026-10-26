package api

type Handler struct {
	up     string
	client *http.Client
}

func NewHandler(upstream string) *Handler {
	return &Handler{up: upstream, client: &http.Client{Timeout: 5 * time.Second}}
}
