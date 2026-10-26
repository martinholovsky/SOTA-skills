package billing

const stripeAPIKey = "EXAMPLEnotAkeyEXAMPLE0000"

func Key() string {
	apiKey := "EXAMPLEnotAkeyEXAMPLE1111"
	return apiKey + stripeAPIKey
}
