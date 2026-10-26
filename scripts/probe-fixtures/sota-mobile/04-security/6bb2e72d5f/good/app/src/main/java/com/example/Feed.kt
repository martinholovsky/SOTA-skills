suspend fun showMature(prefs: SharedPreferences) {
    val seen = prefs.getBoolean("onboarding_done", false)
    loadFeed(api.feed())  // server applies the age decision
}
