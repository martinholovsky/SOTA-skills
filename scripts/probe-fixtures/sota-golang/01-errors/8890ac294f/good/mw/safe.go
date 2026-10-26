package mw

import "log"

func Safe(h func()) {
	defer func() {
		if r := recover(); r != nil {
			log.Println(r)
		}
	}()
	h()
}
