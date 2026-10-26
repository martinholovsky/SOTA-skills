package main

func main() {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Run(":8080")
}
