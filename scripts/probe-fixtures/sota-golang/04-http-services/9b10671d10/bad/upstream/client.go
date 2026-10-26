package upstream

func NewClient() *http.Client {
	return &http.Client{Timeout: 10 * time.Second}
}
