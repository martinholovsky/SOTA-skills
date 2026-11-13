package config

type Refs struct {
	TokenID         string
	SecretName      string `json:"secretName"`
	SecretNamespace string
	TokenURL        string
	PasswordHash    string
}
