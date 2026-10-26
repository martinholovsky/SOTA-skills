namespace Shop.Auth;

public sealed class LoginService(ILogger<LoginService> logger)
{
    public void Attempt(string user)
    {
        logger.LogInformation("Login attempt {User}", user);
    }
}
