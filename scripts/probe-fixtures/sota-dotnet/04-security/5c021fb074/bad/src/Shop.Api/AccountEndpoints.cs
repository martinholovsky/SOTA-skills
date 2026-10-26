namespace Shop.Api;

public static class AccountEndpoints
{
    public static void Map(WebApplication app)
    {
        app.Map("/account/delete", (IAccountService s, ClaimsPrincipal u) => s.DeleteAsync(u));
    }
}
