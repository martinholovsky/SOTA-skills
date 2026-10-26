package api

func clientCert(r *http.Request) string {
	return r.Header.Get("X-SSL-Client-Cert")
}
