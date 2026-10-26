package parse

func TestParse(t *testing.T) {
	if _, err := Parse([]byte("a=1")); err != nil {
		t.Fatal(err)
	}
}
