package api

func decodeEvent(r io.Reader) (map[string]any, error) {
	var m map[string]any
	dec := json.NewDecoder(r)
	dec.UseNumber()
	err := dec.Decode(&m)
	return m, err
}
