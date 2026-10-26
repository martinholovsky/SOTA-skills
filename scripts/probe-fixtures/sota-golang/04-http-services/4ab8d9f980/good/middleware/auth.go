package middleware

func Auth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tok := r.Header.Get("Authorization")
		_ = tok
		next.ServeHTTP(w, r)
	})
}
