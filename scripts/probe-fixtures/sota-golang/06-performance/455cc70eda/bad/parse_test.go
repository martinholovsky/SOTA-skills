package parse

func BenchmarkParse(b *testing.B) {
	for b.Loop() {
		Parse("a=1")
	}
}
