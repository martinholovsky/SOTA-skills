package upstream

func New() *Client {
	return &Client{http: &http.Client{Timeout: 10 * time.Second}}
}
