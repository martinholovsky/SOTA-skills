package ws

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return allowedOrigins[r.Header.Get("Origin")] },
}
