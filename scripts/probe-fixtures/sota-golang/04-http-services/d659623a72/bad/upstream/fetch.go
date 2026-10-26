package upstream

func Fetch(c *http.Client, req *http.Request) error {
	resp, err := c.Do(req)
	if err != nil {
		return err
	}
	_ = resp
	return nil
}
