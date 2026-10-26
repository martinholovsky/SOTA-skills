namespace Shop.Api;

public static class AuthEndpoints
{
    public static void Map(WebApplication app)
    {
        app.MapPost("/login", (LoginRequest req, IAuthService auth) => auth.SignInAsync(req));
    }
}
