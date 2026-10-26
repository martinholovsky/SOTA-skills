fun notify(msg: Message) {
    val preview = stripMarkup(msg.body).take(80)
    val n = NotificationCompat.Builder(ctx, CHANNEL)
        .setContentTitle(getString(R.string.new_message_title))
        .setContentText(getString(R.string.new_message_from, preview))
        .build()
}
