package config

type Signer struct {
	SigningKey  string `json:",omitempty"`
	Credential  []byte
	TenantTokens map[string]string
}
