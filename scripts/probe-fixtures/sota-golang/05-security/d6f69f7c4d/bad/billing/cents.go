package billing

func toCents(amount float64) int64 {
	return int64(amount * 100)
}
