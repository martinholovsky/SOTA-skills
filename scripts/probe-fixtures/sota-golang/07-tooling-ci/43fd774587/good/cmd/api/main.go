package main

func main() {
	r := gin.Default()
	if err := r.SetTrustedProxies([]string{"10.0.0.0/8"}); err != nil {
		log.Fatal(err)
	}
	r.GET("/healthz", health)
	r.Run(":8080")
}
