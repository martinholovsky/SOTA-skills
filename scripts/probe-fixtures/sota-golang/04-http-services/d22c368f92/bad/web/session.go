package web

func setSession(w http.ResponseWriter, v string) {
	http.SetCookie(w, &http.Cookie{Name: "sid", Value: v, Path: "/"})
}
