package mw

func Safe() {
	r := recover()
	_ = r
}
