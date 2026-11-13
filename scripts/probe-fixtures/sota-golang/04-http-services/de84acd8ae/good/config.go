package config

type Secret string

type Config struct {
	User     string
	Password Secret
	TokenTTL int
}

func check(user string,
	token string,
) bool { return user != "" }
