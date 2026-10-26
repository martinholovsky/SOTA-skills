class TokenStore(private val prefs: EncryptedPrefs, private val km: KeyguardManager) {
    fun save(token: String) {
        if (!km.isDeviceSecure()) return degradeToSessionOnly(token)
        prefs.put("session", token)
    }
}
