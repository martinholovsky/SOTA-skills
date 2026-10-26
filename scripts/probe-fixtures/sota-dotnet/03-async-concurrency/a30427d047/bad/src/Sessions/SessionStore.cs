namespace Shop.Sessions;

public sealed class SessionStore
{
    private static readonly Dictionary<string, Session> _sessions = new Dictionary<string, Session>();

    public void Add(Session s) => _sessions[s.Id] = s;
}
