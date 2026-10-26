package upstream

func authorize(req *http.Request, key string) {
	req.Header.Set("Authorization", "Bearer "+key)
}
