package main

import "runtime/debug"

func main() {
	debug.SetMaxStack(4 << 30)
	run()
}
