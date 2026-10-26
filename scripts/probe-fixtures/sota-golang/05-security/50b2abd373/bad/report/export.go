package report

func export(data []byte) (string, error) {
	p := "/tmp/report.csv"
	return p, os.WriteFile(p, data, 0o600)
}
