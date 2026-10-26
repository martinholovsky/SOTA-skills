using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Processing;

namespace Shop.Images;

public static class Thumbnailer
{
    public static async Task MakeAsync(Stream upload, Stream output, CancellationToken ct)
    {
        using var image = await Image.LoadAsync(upload, ct);
        image.Mutate(x => x.Resize(200, 200));
        await image.SaveAsPngAsync(output, ct);
    }
}
