package parse

func BenchmarkParse(b *testing.B) {
	b.ReportAllocs()
	for b.Loop() {
		Parse("a=1")
	}
}
