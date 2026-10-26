using System.Security.Cryptography;

namespace Shop.Auth;

public static class ResetCodes
{
    public static string NewResetToken() => RandomNumberGenerator.GetInt32(100000, 1000000).ToString();
}
