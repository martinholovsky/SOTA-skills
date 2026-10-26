package web

func set(w http.ResponseWriter, id string) {
	http.SetCookie(w, &http.Cookie{
		Name:  "sid",
		Value: id,
		Path:  "/",
	})
}
