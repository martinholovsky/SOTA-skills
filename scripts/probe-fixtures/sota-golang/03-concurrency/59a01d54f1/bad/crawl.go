package crawl

func fetchAll(ctx context.Context, urls []string) {
	for _, u := range urls {
		go func() {
			fetch(ctx, u)
		}()
	}
}
