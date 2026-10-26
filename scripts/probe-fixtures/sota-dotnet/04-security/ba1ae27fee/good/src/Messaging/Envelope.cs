using Newtonsoft.Json;

namespace Shop.Messaging;

public static class Envelope
{
    private static readonly JsonSerializerSettings Settings = new() { TypeNameHandling = TypeNameHandling.None };

    public static OrderMessage? Read(string json) => JsonConvert.DeserializeObject<OrderMessage>(json, Settings);
}
