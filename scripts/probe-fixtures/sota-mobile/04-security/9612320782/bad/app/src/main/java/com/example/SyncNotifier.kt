fun announce(ctx: Context, token: String) {
    val i = Intent("com.example.SYNC_DONE")
    i.putExtra("auth_token", token)
    ctx.sendBroadcast(i)
}
