package api

func pageSize(r *http.Request) (int, error) {
	n, err := strconv.Atoi(r.URL.Query().Get("limit"))
	if err != nil {
		return 0, fmt.Errorf("limit: %w", err)
	}
	return n, nil
}
