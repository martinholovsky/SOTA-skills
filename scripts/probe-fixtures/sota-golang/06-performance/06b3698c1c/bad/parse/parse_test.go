package parse

func TestParse(t *testing.T) {
	if _, err := Parse("a=1"); err != nil {
		t.Fatal(err)
	}
}
