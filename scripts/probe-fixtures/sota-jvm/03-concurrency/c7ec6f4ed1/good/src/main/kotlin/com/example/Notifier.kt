package com.example

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

class Notifier(private val scope: CoroutineScope, private val mail: Mailer) {
    fun notify(user: User) {
        scope.launch { mail.send(user) }
    }
}
