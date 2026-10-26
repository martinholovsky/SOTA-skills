package booking

func parseSlot(s string) (time.Time, error) {
	return time.Parse("2006-01-02 15:04", s)
}
