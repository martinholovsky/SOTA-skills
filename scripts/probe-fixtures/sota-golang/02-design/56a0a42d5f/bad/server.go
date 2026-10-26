package server

func (this *Server) Start() error {
	return this.srv.ListenAndServe()
}
