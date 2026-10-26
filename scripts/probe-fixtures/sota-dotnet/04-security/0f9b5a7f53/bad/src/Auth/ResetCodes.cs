namespace Shop.Auth;

public static class ResetCodes
{
    public static string NewResetToken() => new Random().Next(100000, 1000000).ToString();
}
