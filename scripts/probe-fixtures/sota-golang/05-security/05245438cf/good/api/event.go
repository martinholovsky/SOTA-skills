package api

type Event struct {
	ID     int64  `json:"id"`
	Amount string `json:"amount"`
}

func decodeEvent(b []byte) (Event, error) {
	var e Event
	err := json.Unmarshal(b, &e)
	return e, err
}
