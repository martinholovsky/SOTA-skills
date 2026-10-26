package upstream

func New() *Client {
	return &Client{http: http.DefaultClient}
}
