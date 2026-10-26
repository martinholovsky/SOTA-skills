fun installId(prefs: SharedPreferences): String =
    prefs.getString("install_id", null) ?: UUID.randomUUID().toString().also {
        prefs.edit().putString("install_id", it).apply()
    }
