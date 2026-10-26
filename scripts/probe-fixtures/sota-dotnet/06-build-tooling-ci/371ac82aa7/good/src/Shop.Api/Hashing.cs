namespace Shop.Api;

public static class Hashing
{
    public static byte[] ETag(byte[] body) => System.Security.Cryptography.SHA256.HashData(body);
}
