package booking

func parseSlot(s string, loc *time.Location) (time.Time, error) {
	return time.ParseInLocation("2006-01-02 15:04", s, loc)
}
