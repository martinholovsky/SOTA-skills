package crawl

func fetchAll(ctx context.Context, urls []string) error {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(8)
	for _, u := range urls {
		g.Go(func() error { return fetch(ctx, u) })
	}
	return g.Wait()
}
