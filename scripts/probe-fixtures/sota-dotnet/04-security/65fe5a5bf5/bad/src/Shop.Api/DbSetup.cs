namespace Shop.Api;

public static class DbSetup
{
    public static void Add(WebApplicationBuilder builder) =>
        builder.Services.AddDbContext<ShopDb>(o => o.UseNpgsql(builder.Configuration.GetConnectionString("Shop")).EnableSensitiveDataLogging());
}
