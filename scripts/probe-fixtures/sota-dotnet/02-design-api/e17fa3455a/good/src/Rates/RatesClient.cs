namespace Shop.Rates;

public sealed class RatesClient(IHttpClientFactory factory)
{
    public async Task<string> FetchAsync(CancellationToken ct)
    {
        var http = factory.CreateClient("rates");
        return await http.GetStringAsync("https://rates.example.com/latest", ct);
    }
}
