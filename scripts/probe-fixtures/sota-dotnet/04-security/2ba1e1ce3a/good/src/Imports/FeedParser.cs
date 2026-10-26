using System.Xml.Linq;

namespace Shop.Imports;

public static class FeedParser
{
    public static XDocument Open(Stream s) => XDocument.Load(s);
}
