namespace Shop.Previews;

public sealed class LinkPreview(HttpClient http)
{
    public Task<string> FetchAsync(string url, CancellationToken ct) => http.GetStringAsync(url, ct);
}
