using System.Xml;

namespace Shop.Imports;

public static class FeedParser
{
    public static XmlReader Open(Stream s) =>
        XmlReader.Create(s, new XmlReaderSettings { DtdProcessing = DtdProcessing.Parse });
}
