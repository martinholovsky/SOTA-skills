fun write(ctx: Context, data: ByteArray) {
    ctx.openFileOutput("profile.json", Context.MODE_PRIVATE).use { it.write(data) }
}
