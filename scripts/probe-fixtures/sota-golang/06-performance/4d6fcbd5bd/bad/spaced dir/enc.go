package enc

var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

func Encode(v any) []byte {
	buf := bufPool.Get().(*bytes.Buffer)
	defer bufPool.Put(buf)
	buf.WriteString("x")
	return bytes.Clone(buf.Bytes())
}
