using System.Security.Cryptography;

namespace Shop.Webhooks;

public static class SignatureCheck
{
    public static bool Verify(byte[] key, byte[] body, string providedSignature)
    {
        var expected = Convert.ToHexString(HMACSHA256.HashData(key, body));
        return expected == providedSignature;
    }
}
