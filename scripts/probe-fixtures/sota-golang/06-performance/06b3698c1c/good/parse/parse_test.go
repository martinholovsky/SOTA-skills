package parse

func TestParse(t *testing.T) {
	if _, err := Parse("a=1"); err != nil {
		t.Fatal(err)
	}
}

func BenchmarkParse(b *testing.B) {
	b.ReportAllocs()
	for b.Loop() {
		Parse("a=1")
	}
}
