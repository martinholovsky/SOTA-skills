package main

func handler() http.Handler {
	cop := http.NewCrossOriginProtection()
	cop.AddInsecureBypassPattern("POST /webhooks/")
	return cop.Handler(routes())
}
