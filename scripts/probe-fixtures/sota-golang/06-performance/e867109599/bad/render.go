package render

func join(msgs []Message) string {
	var s string
	for _, m := range msgs {
		s += m.Text + "\n"
	}
	return s
}
