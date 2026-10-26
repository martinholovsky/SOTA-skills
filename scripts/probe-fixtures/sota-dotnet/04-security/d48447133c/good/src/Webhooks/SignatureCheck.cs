using System.Security.Cryptography;

namespace Shop.Webhooks;

public static class SignatureCheck
{
    public static bool Verify(byte[] key, byte[] body, byte[] provided)
    {
        var expected = HMACSHA256.HashData(key, body);
        return CryptographicOperations.FixedTimeEquals(expected, provided);
    }
}
