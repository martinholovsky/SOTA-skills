package api

func Orders(w http.ResponseWriter, r *http.Request) {
	tok := r.Header.Get("Authorization")
	_ = tok
}
