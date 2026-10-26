package report

func export(data []byte) (string, error) {
	f, err := os.CreateTemp("", "report-*.csv")
	if err != nil {
		return "", err
	}
	defer f.Close()
	_, err = f.Write(data)
	return f.Name(), err
}
