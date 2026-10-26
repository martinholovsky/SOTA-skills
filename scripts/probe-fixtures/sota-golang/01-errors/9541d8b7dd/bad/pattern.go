package pattern

type Pattern struct{ s string }

func Compile(s string) *Pattern {
	if s == "" {
		panic("empty pattern")
	}
	return &Pattern{s}
}
