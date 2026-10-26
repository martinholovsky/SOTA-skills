using System.Text.Json;

namespace Shop.Api;

public static class JsonSetup
{
    public static readonly JsonSerializerOptions Options = new() { MaxDepth = 256 };
}
