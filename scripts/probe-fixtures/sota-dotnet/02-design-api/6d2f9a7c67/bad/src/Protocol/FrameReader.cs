namespace Shop.Protocol;

public static class FrameReader
{
    public static byte[] Read(BinaryReader reader)
    {
        var length = reader.ReadInt32();
        var payload = new byte[length];
        reader.BaseStream.ReadExactly(payload);
        return payload;
    }
}
