using System.Security.Cryptography;

namespace Shop.Auth;

public static class PasswordHasher
{
    public static byte[] Hash(string password, byte[] salt)
    {
        using var kdf = new Rfc2898DeriveBytes(password, salt);
        return kdf.GetBytes(32);
    }
}
