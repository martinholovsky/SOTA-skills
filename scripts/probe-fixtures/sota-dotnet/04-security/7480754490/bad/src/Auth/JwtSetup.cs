namespace Shop.Auth;

public static class JwtSetup
{
    public static TokenValidationParameters Parameters(string issuer) => new()
    {
        ValidIssuer = issuer,
        ValidateAudience = false,
    };
}
