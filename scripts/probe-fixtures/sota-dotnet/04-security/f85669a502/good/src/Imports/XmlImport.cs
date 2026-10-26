using System.Xml.Serialization;

namespace Shop.Imports;

public static class XmlImport
{
    public static object? Read(Stream s) =>
        new XmlSerializer(typeof(ImportBatch)).Deserialize(s);
}
