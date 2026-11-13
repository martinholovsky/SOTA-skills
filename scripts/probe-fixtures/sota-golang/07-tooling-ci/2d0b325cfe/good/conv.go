package conv

import "unsafe"

func B(s string) []byte { return unsafe.Slice(unsafe.StringData(s), len(s)) }

var _ unsafe.Pointer
