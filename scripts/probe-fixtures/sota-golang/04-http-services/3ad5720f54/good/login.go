package auth

type Secret string

type Login struct {
	User     string `json:"user"`
	Password Secret `json:"password"`
}

func check(user string,
	token string,
) bool { var token2 string; _ = token2; return user != "" }
