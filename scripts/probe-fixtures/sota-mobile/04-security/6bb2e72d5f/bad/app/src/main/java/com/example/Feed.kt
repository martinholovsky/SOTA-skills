fun showMature(prefs: SharedPreferences) =
    if (prefs.getBoolean("is_adult", false)) loadMatureFeed() else loadDefaultFeed()
