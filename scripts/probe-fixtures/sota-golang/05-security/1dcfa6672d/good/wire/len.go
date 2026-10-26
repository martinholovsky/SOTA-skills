package wire

import (
	"errors"
	"math"
)

type Req struct{ Length int }

const small = uint8(3)

var errLen = errors.New("length out of range")

func Len(req Req) (int32, error) {
	if req.Length < 0 || req.Length > math.MaxInt32 {
		return 0, errLen
	}
	return int32(req.Length), nil
}
