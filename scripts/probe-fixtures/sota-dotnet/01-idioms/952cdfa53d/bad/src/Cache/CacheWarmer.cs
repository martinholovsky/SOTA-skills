namespace Shop.Cache;

public sealed class CacheWarmer(ICache cache)
{
    public void Warm()
    {
        try
        {
            cache.Load();
        }
        catch (Exception)
        {
        }
    }
}
