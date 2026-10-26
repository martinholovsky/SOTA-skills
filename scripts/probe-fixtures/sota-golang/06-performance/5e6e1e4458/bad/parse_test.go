package parse

func BenchmarkParse(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		Parse("a=1")
	}
}
