package match

func New(p string) (*regexp2.Regexp, error) {
	re, err := regexp2.Compile(p, regexp2.None)
	if err != nil {
		return nil, err
	}
	re.MatchTimeout = 100 * time.Millisecond
	return re, nil
}
