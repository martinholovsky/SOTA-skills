package event

func encode(e Event) ([]byte, error) {
	data, err := json.Marshal(e)
	if err != nil {
		return nil, fmt.Errorf("encode event %s: %w", e.ID, err)
	}
	return data, nil
}
