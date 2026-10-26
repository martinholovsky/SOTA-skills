namespace Shop.Cache;

public sealed class CacheWarmer(ICache cache, ILogger<CacheWarmer> log)
{
    public void Warm()
    {
        try
        {
            cache.Load();
        }
        catch (TimeoutException ex)
        {
            log.LogWarning(ex, "cache warm-up timed out; serving cold");
        }
    }
}
