namespace Shop.Api;

public static class CorsSetup
{
    public static void Add(IServiceCollection services) =>
        services.AddCors(o => o.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));
}
