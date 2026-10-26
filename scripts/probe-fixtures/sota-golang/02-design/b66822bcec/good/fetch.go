package fetch

func Fetch(ctx context.Context, id string) (*Item, error) {
	return load(ctx, id)
}
