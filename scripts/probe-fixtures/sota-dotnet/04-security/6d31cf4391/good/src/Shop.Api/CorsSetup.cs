namespace Shop.Api;

public static class CorsSetup
{
    public static void Add(IServiceCollection services) =>
        services.AddCors(o => o.AddDefaultPolicy(p => p.WithOrigins("https://app.example.com").WithMethods("GET", "POST").WithHeaders("Content-Type")));
}
