using System.Diagnostics.CodeAnalysis;

namespace Shop.Api;

public static class Hashing
{
    [SuppressMessage("Security", "CA5351:Do Not Use Broken Cryptographic Algorithms", Justification = "legacy")]
    public static byte[] ETag(byte[] body) => System.Security.Cryptography.MD5.HashData(body);
}
