namespace Shop.Previews;

public sealed class LinkPreview(HttpClient http)
{
    public Task<string> FetchAsync(int productId, CancellationToken ct) => http.GetStringAsync($"/products/{productId}/preview", ct);
}
