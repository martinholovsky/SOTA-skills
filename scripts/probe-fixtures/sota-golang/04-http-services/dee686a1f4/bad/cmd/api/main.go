package main

func main() {
	gin.SetMode(gin.DebugMode)
	r := gin.New()
	r.Run(":8080")
}
