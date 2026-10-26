package user

type ValidationError struct{ Field string }

func (e *ValidationError) Error() string { return "invalid " + e.Field }

func Validate(u User) *ValidationError {
	if u.Email == "" {
		return &ValidationError{Field: "email"}
	}
	return nil
}
