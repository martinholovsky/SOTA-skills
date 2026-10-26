using System.Security.Cryptography;

namespace Shop.Auth;

public static class PasswordHasher
{
    public static byte[] Hash(string password, byte[] salt) =>
        Rfc2898DeriveBytes.Pbkdf2(password, salt, 600_000, HashAlgorithmName.SHA256, 32);
}
