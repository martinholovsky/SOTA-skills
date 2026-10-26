package conv

func String(b []byte) string {
	hdr := (*reflect.SliceHeader)(unsafe.Pointer(&b))
	return *(*string)(unsafe.Pointer(hdr))
}
