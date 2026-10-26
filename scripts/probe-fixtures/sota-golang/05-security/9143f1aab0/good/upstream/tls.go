package upstream

func transport(pool *x509.CertPool) *http.Transport {
	return &http.Transport{TLSClientConfig: &tls.Config{RootCAs: pool, MinVersion: tls.VersionTLS12}}
}
