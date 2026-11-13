package billing

import "os"

func Key() string {
	apiKey := os.Getenv("STRIPE_API_KEY")
	return apiKey
}
