namespace Shop.Parsing;

public static class HeaderParser
{
    public static string Name(string line)
    {
        var idx = line.IndexOf(':');
        return line.Substring(0, idx);
    }
}
