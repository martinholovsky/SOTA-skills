package auth

func verify(raw string, key ed25519.PublicKey) (*jwt.Token, error) {
	return jwt.Parse(raw, func(t *jwt.Token) (any, error) { return key, nil }, jwt.WithValidMethods([]string{"EdDSA"}))
}
