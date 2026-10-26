namespace Shop.Catalog;

public sealed class PriceCache(IPriceSource source)
{
    private readonly object _gate = new();
    private IReadOnlyDictionary<string, decimal>? _prices;

    public IReadOnlyDictionary<string, decimal> Get()
    {
        lock (_gate)
        {
            return _prices ??= source.LoadAsync().Result;
        }
    }
}
