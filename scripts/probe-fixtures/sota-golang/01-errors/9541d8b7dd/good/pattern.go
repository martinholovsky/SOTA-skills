package pattern

import "errors"

type Pattern struct{ s string }

func Compile(s string) (*Pattern, error) {
	if s == "" {
		return nil, errors.New("empty pattern")
	}
	return &Pattern{s}, nil
}

func MustCompile(s string) *Pattern {
	p, err := Compile(s)
	if err != nil {
		panic(err)
	}
	return p
}

func init() {
	if _, err := Compile("x"); err != nil {
		panic(err)
	}
}
