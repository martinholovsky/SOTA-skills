using System.Runtime.Serialization.Formatters.Binary;

namespace Shop.Legacy;

public static class SessionSerializer
{
    public static object Read(Stream s) => new BinaryFormatter().Deserialize(s);
}
