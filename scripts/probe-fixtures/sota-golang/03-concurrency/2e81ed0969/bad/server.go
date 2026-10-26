package server

func (s *Server) Start(ctx context.Context) error {
	go s.refreshCache(ctx)
	return s.http.ListenAndServe()
}
