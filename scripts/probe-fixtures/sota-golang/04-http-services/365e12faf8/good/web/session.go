package web

func set(w http.ResponseWriter, id string) {
	http.SetCookie(w, &http.Cookie{
		Name:     "sid",
		Value:    id,
		HttpOnly: true,
		Secure:   true,
	})

	http.SetCookie(w, &http.Cookie{
		Name:     "theme",
		Value:    "dark",
		HttpOnly: true,
		Secure:   true,
	})
}
