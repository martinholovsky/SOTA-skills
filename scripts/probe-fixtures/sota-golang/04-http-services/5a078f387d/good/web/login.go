package web

func login(c *gin.Context) {
	tok := issue(c)
	c.SetSameSite(http.SameSiteLaxMode)
	c.SetCookie("session", tok, 3600, "/", "", true, true)
}
