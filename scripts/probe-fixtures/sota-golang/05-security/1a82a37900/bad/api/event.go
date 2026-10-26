package api

func decodeEvent(r io.Reader) (map[string]any, error) {
	var m map[string]any
	err := json.NewDecoder(r).Decode(&m)
	return m, err
}
