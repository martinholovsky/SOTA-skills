fun deviceProof(ctx: Context): String =
    Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ANDROID_ID)
