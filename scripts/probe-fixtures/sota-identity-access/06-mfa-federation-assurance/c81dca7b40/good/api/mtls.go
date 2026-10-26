package api

func clientCert(r *http.Request) *x509.Certificate {
	return r.TLS.PeerCertificates[0]
}
