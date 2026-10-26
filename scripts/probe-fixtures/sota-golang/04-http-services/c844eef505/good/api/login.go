package api

import "net/http"

func Login(w http.ResponseWriter, r *http.Request) {
	next := r.URL.Query().Get("next")
	if !isLocalPath(next) {
		next = "/"
	}
	http.Redirect(w, r, next, http.StatusFound)
}
