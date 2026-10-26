fun notify(msg: Message) {
    val n = NotificationCompat.Builder(ctx, CHANNEL)
        .setContentTitle("New message")
        .setContentText("${msg.sender}: ${msg.body}")
        .build()
}
