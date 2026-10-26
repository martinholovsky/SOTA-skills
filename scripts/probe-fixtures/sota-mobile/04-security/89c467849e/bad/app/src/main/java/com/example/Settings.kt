fun keepPermissions(activity: Activity) {
    activity.startActivity(IntentCompat.createManageUnusedAppRestrictionsIntent(activity, activity.packageName))
}
