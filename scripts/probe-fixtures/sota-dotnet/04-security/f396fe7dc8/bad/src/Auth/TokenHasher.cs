using System.Security.Cryptography;

namespace Shop.Auth;

public static class TokenHasher
{
    public static byte[] Hash(byte[] token) => MD5.HashData(token);
}
