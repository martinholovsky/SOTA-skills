fun canExport(prefs: SharedPreferences): Boolean =
    prefs.getBoolean("is_premium", false)
