fun write(ctx: Context, data: ByteArray) {
    ctx.openFileOutput("profile.json", Context.MODE_WORLD_READABLE).use { it.write(data) }
}
