package server

func (s *Server) Start() error {
	return s.srv.ListenAndServe()
}
