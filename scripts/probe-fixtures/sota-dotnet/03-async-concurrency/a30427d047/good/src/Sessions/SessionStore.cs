using System.Collections.Concurrent;

namespace Shop.Sessions;

public sealed class SessionStore
{
    private static readonly ConcurrentDictionary<string, Session> _sessions = new ConcurrentDictionary<string, Session>();

    public void Add(Session s) => _sessions[s.Id] = s;
}
