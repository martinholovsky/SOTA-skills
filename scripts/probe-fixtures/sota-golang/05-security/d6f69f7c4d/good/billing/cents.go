package billing

func toCents(amount float64) int64 {
	return int64(math.Round(amount * 100))
}
