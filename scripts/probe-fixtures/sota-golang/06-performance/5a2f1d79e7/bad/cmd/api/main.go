package main

func main() {
	ballast := make([]byte, 10<<30)
	defer runtime.KeepAlive(ballast)
	run()
}
