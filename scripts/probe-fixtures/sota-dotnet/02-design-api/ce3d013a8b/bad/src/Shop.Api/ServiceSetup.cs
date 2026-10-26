namespace Shop.Api;

public static class ServiceSetup
{
    public static void Add(IServiceCollection services)
    {
        services.AddDbContext<ShopDb>();
        services.AddSingleton<IPriceCache, PriceCache>();
    }
}
