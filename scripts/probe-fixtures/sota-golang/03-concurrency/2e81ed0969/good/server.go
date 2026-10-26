package server

func (s *Server) Start(ctx context.Context) error {
	g, ctx := errgroup.WithContext(ctx)
	g.Go(func() error { return s.refreshCache(ctx) })
	g.Go(s.http.ListenAndServe)
	return g.Wait()
}
