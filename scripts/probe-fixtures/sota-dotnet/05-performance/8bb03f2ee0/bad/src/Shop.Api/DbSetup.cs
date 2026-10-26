namespace Shop.Api;

public static class DbSetup
{
    public static void Add(IServiceCollection services, string cs) =>
        services.AddDbContext<ShopDb>(o => o.UseLazyLoadingProxies().UseNpgsql(cs));
}
