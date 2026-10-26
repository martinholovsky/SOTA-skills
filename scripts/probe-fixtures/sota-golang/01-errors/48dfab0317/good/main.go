package main

import "runtime/debug"

func main() {
	debug.SetGCPercent(200)
	run()
}
