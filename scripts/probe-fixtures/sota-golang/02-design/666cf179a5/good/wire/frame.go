package wire

func payload(buf []byte, hdr Header) ([]byte, error) {
	off, n := int(hdr.Offset), int(hdr.Len)
	if off < 0 || n < 0 || off > len(buf)-n {
		return nil, errBadFrame
	}
	return buf[off : off+n], nil
}
