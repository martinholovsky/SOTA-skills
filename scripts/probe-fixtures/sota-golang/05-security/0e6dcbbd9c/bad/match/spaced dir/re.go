package match

func New(p string) (*regexp2.Regexp, error) {
	return regexp2.Compile(p, regexp2.None)
}
