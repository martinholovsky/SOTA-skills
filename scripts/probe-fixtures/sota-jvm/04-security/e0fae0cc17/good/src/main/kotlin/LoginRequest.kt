package app

data class LoginRequest(
    val username: String,
    val rememberMe: Boolean,
)
