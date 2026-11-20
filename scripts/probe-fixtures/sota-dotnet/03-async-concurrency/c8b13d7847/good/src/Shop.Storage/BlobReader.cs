namespace Shop.Storage;

public static class BlobReader
{
    public static async Task<int> ReadAsync(Stream stream, Memory<byte> buffer, CancellationToken ct)
    {
        return await stream.ReadAsync(buffer, ct).ConfigureAwait(false);
    }
}
