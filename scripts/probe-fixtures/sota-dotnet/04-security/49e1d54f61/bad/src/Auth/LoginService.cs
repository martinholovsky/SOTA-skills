namespace Shop.Auth;

public sealed class LoginService(ILogger<LoginService> logger)
{
    public void Attempt(string user, string password)
    {
        logger.LogInformation("Login attempt {User} {Password}", user, password);
    }
}
