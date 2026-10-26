using Newtonsoft.Json;

namespace Shop.Messaging;

public static class Envelope
{
    private static readonly JsonSerializerSettings Settings = new() { TypeNameHandling = TypeNameHandling.Auto };

    public static object? Read(string json) => JsonConvert.DeserializeObject(json, Settings);
}
