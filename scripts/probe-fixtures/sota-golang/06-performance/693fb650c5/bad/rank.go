package rank

func byScore(items []Item) {
	sort.Slice(items, func(i, j int) bool { return items[i].Score > items[j].Score })
}
