using System.Runtime.InteropServices;

namespace Shop.Native;

internal static partial class Zlib
{
    [DllImport("libz", EntryPoint = "uncompress")]
    internal static extern int Uncompress(byte[] dest, ref uint destLen, byte[] source, uint sourceLen);
}
