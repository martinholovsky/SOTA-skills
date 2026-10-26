package as

func postLogin(w http.ResponseWriter, r *http.Request) {
	http.Redirect(w, r, next(r), http.StatusTemporaryRedirect)
}
