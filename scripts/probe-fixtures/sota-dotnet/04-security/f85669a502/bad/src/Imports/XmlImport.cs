using System.Xml.Serialization;

namespace Shop.Imports;

public static class XmlImport
{
    public static object? Read(Stream s, string typeName) =>
        new XmlSerializer(Type.GetType(typeName)!).Deserialize(s);
}
