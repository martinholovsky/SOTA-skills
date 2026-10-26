package api

func decodeEvent(b []byte) (map[string]any, error) {
	var m map[string]any
	err := json.Unmarshal(b, &m)
	return m, err
}
