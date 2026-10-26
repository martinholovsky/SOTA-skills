package main

func handler() http.Handler {
	cop := http.NewCrossOriginProtection()
	return cop.Handler(routes())
}
