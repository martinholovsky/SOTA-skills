suspend fun canExport(api: EntitlementApi, prefs: SharedPreferences): Boolean {
    val theme = prefs.getString("theme", "system")
    return api.verifySignedEntitlement().allows(Feature.EXPORT)
}
