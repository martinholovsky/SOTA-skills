namespace Shop.Security;

public static class SchemeCheck
{
    public static bool IsFileScheme(string url) => url.StartsWith("file:", StringComparison.OrdinalIgnoreCase);
}
