namespace Shop.Sync;

public sealed class CatalogSync(HttpClient http)
{
    public Task SyncAsync(IEnumerable<Uri> feeds, CancellationToken ct) =>
        Task.WhenAll(feeds.Select(f => http.GetStringAsync(f, ct)));
}
