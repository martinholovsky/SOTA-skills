package fetch

func Fetch(id string, ctx context.Context) (*Item, error) {
	return load(ctx, id)
}
