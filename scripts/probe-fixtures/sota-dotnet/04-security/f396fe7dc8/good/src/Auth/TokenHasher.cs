using System.Security.Cryptography;

namespace Shop.Auth;

public static class TokenHasher
{
    public static byte[] Hash(byte[] token) => SHA256.HashData(token);
}
