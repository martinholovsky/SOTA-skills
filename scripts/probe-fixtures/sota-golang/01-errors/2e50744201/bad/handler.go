package api

func pageSize(r *http.Request) int {
	n, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	return n
}
