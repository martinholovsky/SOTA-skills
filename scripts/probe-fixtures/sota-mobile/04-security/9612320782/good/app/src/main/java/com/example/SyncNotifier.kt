fun announce(ctx: Context, syncId: String) {
    val i = Intent("com.example.SYNC_DONE").setPackage(ctx.packageName)
    i.putExtra("sync_id", syncId)
    ctx.sendBroadcast(i, "com.example.permission.SYNC")
    ContextCompat.registerReceiver(ctx, receiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED)
}
