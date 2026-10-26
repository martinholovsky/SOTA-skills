using System.Text.Json;

namespace Shop.Legacy;

public static class SessionSerializer
{
    public static SessionState? Read(Stream s) => JsonSerializer.Deserialize<SessionState>(s);
}
