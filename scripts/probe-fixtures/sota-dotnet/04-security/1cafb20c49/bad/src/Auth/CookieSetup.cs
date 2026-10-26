namespace Shop.Auth;

public static class CookieSetup
{
    public static CookieOptions Session() => new()
    {
        Secure = true,
        HttpOnly = true,
        Domain = ".example.com",
    };
}
