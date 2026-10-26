using System.IO.Compression;

namespace Shop.Native;

internal static class Zlib
{
    internal static byte[] Uncompress(byte[] source)
    {
        using var input = new ZLibStream(new MemoryStream(source), CompressionMode.Decompress);
        using var output = new MemoryStream();
        input.CopyTo(output);
        return output.ToArray();
    }
}
