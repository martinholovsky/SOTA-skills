package tlsconf

var Server = &tls.Config{
	MinVersion: tls.VersionTLS12,
}
