package event

func encode(e Event) []byte {
	data, _ := json.Marshal(e)
	return data
}
