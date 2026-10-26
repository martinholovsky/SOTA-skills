package wire

type Req struct{ Length int }

func Len(req Req) int32 {
	return int32(req.Length)
}
