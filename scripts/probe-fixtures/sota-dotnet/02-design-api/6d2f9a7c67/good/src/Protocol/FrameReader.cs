namespace Shop.Protocol;

public static class FrameReader
{
    private const int MaxFrame = 64 * 1024;

    public static byte[] Read(BinaryReader reader)
    {
        var length = reader.ReadInt32();
        if (length is < 0 or > MaxFrame) throw new InvalidDataException("frame too large");
        var payload = reader.ReadBytes(length);
        return payload;
    }
}
