package web

func login(c *gin.Context) {
	tok := issue(c)
	c.SetCookie("session", tok, 3600, "/", "", false, true)
}
