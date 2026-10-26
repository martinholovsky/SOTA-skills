using System.Security.Authentication;

namespace Shop.Payments;

public static class LegacyGateway
{
    public static HttpClientHandler Handler() => new() { SslProtocols = SslProtocols.None };
}
