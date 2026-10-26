package tlsconf

func Config() *tls.Config {
	return &tls.Config{
		MinVersion: tls.VersionTLS12,
	}
}
