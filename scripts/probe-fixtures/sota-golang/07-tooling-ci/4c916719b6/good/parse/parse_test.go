package parse

func TestParse(t *testing.T) {
	if _, err := Parse([]byte("a=1")); err != nil {
		t.Fatal(err)
	}
}

func FuzzParse(f *testing.F) {
	f.Add([]byte("a=1"))
	f.Fuzz(func(t *testing.T, b []byte) { Parse(b) })
}
