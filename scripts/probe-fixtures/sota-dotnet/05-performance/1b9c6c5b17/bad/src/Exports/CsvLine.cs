namespace Shop.Exports;

public static class CsvLine
{
    public static string Build(IEnumerable<Item> items)
    {
        var csv = "";
        foreach (var item in items)
        {
            csv += item.Name + ",";
        }
        return csv;
    }
}
