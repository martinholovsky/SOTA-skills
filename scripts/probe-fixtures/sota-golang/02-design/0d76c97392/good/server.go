package server

import "time"

type Config struct {
	Addr    string
	Timeout time.Duration
}

type Server struct{ cfg Config }

func New(cfg Config) *Server {
	if cfg.Timeout == 0 {
		cfg.Timeout = 30 * time.Second
	}
	return &Server{cfg: cfg}
}
