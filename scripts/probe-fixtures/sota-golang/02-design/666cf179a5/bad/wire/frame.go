package wire

func payload(buf []byte, hdr Header) []byte {
	return buf[hdr.Offset : hdr.Offset+hdr.Len]
}
