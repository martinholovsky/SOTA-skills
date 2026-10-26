package upstream

func (c *Client) Fetch(ctx context.Context, url string) (int, error) {
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, err
	}
	return resp.StatusCode, nil
}
