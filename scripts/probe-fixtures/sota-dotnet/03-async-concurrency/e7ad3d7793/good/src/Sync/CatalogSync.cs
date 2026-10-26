using System.Threading.Channels;

namespace Shop.Sync;

public sealed class CatalogSync(HttpClient http)
{
    public async Task SyncAsync(ChannelReader<Uri> feeds, CancellationToken ct)
    {
        await foreach (var feed in feeds.ReadAllAsync(ct))
        {
            await http.GetStringAsync(feed, ct);
        }
    }
}
