package up

import (
	"net/http"
	"time"
)

func New(t http.RoundTripper) *http.Client {
	return &http.Client{
		Timeout:   10 * time.Second,
		Transport: t,
	}
}
