namespace Shop.Catalog;

public sealed class PriceCache(IPriceSource source)
{
    private readonly SemaphoreSlim _gate = new(1, 1);
    private IReadOnlyDictionary<string, decimal>? _prices;

    public async Task<IReadOnlyDictionary<string, decimal>> GetAsync(CancellationToken ct)
    {
        await _gate.WaitAsync(ct);
        try
        {
            return _prices ??= await source.LoadAsync(ct);
        }
        finally
        {
            _gate.Release();
        }
    }
}
