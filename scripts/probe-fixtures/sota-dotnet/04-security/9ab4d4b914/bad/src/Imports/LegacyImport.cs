using System.Data;

namespace Shop.Imports;

public static class LegacyImport
{
    public static DataSet Read(Stream upload)
    {
        var ds = new DataSet();
        ds.ReadXml(upload);
        return ds;
    }
}
