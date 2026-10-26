package auth

import "math/rand"

func resetCode() int {
	return 100000 + rand.Intn(900000)
}
