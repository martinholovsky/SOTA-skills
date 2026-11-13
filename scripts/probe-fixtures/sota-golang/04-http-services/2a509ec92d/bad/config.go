package config

type Config struct {
	User, Password string
	DBPassword    *string `yaml:"db_password"`
	Pwd           string
}
