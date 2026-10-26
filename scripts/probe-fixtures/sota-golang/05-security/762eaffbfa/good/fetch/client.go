package fetch

func NewClient() *http.Client {
	d := &net.Dialer{
		Timeout:        5 * time.Second,
		ControlContext: denyInternal,
	}
	return &http.Client{Timeout: 10 * time.Second, Transport: &http.Transport{DialContext: d.DialContext}}
}
