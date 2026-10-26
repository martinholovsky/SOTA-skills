fun askLocation(activity: Activity) {
    activity.requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION), REQ_LOCATION)
}
