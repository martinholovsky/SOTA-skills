package main

func main() {
	r := gin.Default()
	r.GET("/healthz", health)
	r.Run(":8080")
}
