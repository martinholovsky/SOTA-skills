namespace Shop.Previews;

public static class PreviewClient
{
    public static IHttpClientBuilder Add(IServiceCollection services) =>
        services.AddHttpClient("preview");
}
