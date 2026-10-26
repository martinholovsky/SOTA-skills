using System.Diagnostics.CodeAnalysis;

namespace Shop.Api;

public static class Hashing
{
    [SuppressMessage("Security", "CA5351:Do Not Use Broken Cryptographic Algorithms", Justification = "ETag fingerprint only; never used for integrity or authentication")]
    public static byte[] ETag(byte[] body) => System.Security.Cryptography.MD5.HashData(body);
}
