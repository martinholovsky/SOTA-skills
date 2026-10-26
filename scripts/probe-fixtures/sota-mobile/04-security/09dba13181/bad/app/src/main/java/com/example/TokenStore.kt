class TokenStore(private val prefs: EncryptedPrefs) {
    fun save(token: String) {
        prefs.put("session", token)
    }
}
