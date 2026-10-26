package wire

func decodeItems(r io.Reader) ([]Item, error) {
	var hdr Header
	if err := binary.Read(r, binary.BigEndian, &hdr); err != nil {
		return nil, err
	}
	items := make([]Item, hdr.Count)
	return items, readAll(r, items)
}
