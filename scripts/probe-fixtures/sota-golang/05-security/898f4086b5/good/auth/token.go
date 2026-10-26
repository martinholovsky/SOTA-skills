package auth

import "crypto/rand"

func resetToken() string {
	return rand.Text()
}
