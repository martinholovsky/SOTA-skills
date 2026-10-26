namespace Shop.Rates;

public sealed class RatesClient
{
    public async Task<string> FetchAsync(CancellationToken ct)
    {
        using var http = new HttpClient();
        return await http.GetStringAsync("https://rates.example.com/latest", ct);
    }
}
