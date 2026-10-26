package wire

const maxItems = 1 << 16

func decodeItems(r io.Reader) ([]Item, error) {
	var hdr Header
	if err := binary.Read(r, binary.BigEndian, &hdr); err != nil {
		return nil, err
	}
	n := int(hdr.Count)
	if n > maxItems {
		return nil, fmt.Errorf("item count %d exceeds %d", n, maxItems)
	}
	items := make([]Item, n)
	return items, readAll(r, items)
}
