package rank

func byScore(items []Item) {
	slices.SortFunc(items, func(a, b Item) int { return cmp.Compare(b.Score, a.Score) })
}
