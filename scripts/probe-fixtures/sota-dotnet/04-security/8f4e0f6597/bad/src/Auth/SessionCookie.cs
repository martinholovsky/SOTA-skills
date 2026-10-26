namespace Shop.Auth;

public static class SessionCookie
{
    public static void Issue(HttpResponse response, string sessionId)
    {
        response.Cookies.Append("sid", sessionId);
    }
}
