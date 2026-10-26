package price

func parse(s string) (float64, error) {
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return 0, errNotFinite
	}
	return v, nil
}
