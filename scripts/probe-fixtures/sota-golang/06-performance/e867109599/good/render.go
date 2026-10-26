package render

func join(msgs []Message) string {
	var b strings.Builder
	for _, m := range msgs {
		b.WriteString(m.Text)
		b.WriteByte('\n')
	}
	return b.String()
}
