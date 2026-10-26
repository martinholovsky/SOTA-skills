fun remember(prefs: SharedPreferences, user: String) {
    prefs.edit().putString("username", user).apply()
}
