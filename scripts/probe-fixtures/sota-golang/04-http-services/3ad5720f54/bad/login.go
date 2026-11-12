package auth

type Login struct {
	User     string `json:"user"`
	Password string `json:"password"`
}
