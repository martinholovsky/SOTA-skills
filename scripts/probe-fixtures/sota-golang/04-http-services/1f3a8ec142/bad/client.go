package up

import "net/http"

func New(t http.RoundTripper) *http.Client {
	return &http.Client{
		Transport: t,
	}
}
