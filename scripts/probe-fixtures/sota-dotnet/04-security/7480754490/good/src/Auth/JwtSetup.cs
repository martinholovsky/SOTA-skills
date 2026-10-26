namespace Shop.Auth;

public static class JwtSetup
{
    public static TokenValidationParameters Parameters(string issuer, string audience) => new()
    {
        ValidIssuer = issuer,
        ValidAudience = audience,
        ValidateAudience = true,
    };
}
