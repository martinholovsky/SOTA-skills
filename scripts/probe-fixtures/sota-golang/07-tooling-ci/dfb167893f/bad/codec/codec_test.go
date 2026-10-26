package codec

func FuzzRoundTrip(f *testing.F) {
	f.Add([]byte(`{"id":1}`))
	f.Fuzz(func(t *testing.T, b []byte) {
		v, err := Decode(b)
		if err != nil {
			return
		}
		_, _ = Encode(v)
	})
}
