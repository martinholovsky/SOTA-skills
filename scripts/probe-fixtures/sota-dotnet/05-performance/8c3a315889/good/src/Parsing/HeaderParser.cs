namespace Shop.Parsing;

public static class HeaderParser
{
    public static ReadOnlySpan<char> Name(ReadOnlySpan<char> line)
    {
        var idx = line.IndexOf(':');
        return line[..idx];
    }
}
