package com.example

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class Notifier(private val mail: Mailer) {
    fun notify(user: User) {
        GlobalScope.launch { mail.send(user) }
    }
}
