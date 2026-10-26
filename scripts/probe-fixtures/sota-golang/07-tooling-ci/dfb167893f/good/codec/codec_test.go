package codec

func FuzzRoundTrip(f *testing.F) {
	f.Add([]byte(`{"id":1}`))
	f.Fuzz(func(t *testing.T, b []byte) {
		v, err := Decode(b)
		if err != nil {
			return
		}
		out, err := Encode(v)
		if err != nil {
			t.Fatal(err)
		}
		if v2, err := Decode(out); err != nil || !reflect.DeepEqual(v, v2) {
			t.Fatalf("round trip: %v != %v (%v)", v, v2, err)
		}
	})
}
