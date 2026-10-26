fun remember(prefs: SharedPreferences, user: String, pwd: String) {
    prefs.edit().putString("username", user).putString("password", pwd).apply()
}
