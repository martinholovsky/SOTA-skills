namespace Shop.Api;

public static class ProxySetup
{
    public static void Add(IServiceCollection services) => services.Configure<ForwardedHeadersOptions>(o =>
    {
        o.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
        o.KnownProxies.Clear();
    });
}
