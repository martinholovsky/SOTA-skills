package upstream

func Ping(u string) error {
	resp, err := http.Get(u)
	if err != nil {
		return err
	}
	_ = resp
	return nil
}
